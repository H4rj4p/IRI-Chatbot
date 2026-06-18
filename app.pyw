import json
import os
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pymysql
import pymysql.cursors
import requests
from flask import Flask, jsonify, request, send_file


BASE_DIR = Path(__file__).resolve().parent
MAX_ROWS = 100

app = Flask(__name__)


def load_local_settings():
    path = BASE_DIR / "local.settings.json"
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as handle:
        settings = json.load(handle)

    for name, value in settings.get("Values", {}).items():
        if value is None:
            continue
        os.environ.setdefault(name, str(value))


load_local_settings()


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def load_text_file(file_name):
    path = BASE_DIR / file_name
    return path.read_text(encoding="utf-8") if path.exists() else ""


def parse_connection_string(connection_string):
    values = {}
    for part in connection_string.split(";"):
        if not part.strip() or "=" not in part:
            continue
        key, value = part.split("=", 1)
        values[key.strip().lower()] = value.strip()
    return values


def get_connection_args():
    connection_string = os.environ.get("SqlConnectionString")
    if not connection_string or not connection_string.strip():
        return None

    values = parse_connection_string(connection_string)
    host_override = os.environ.get("MySqlHost", "").strip()

    host = (
        values.get("server")
        or values.get("host")
        or values.get("data source")
        or "localhost"
    )
    if host_override:
        host = host_override

    try:
        port = int(values.get("port", "3306"))
    except ValueError:
        port = 3306

    return {
        "host": host,
        "port": port,
        "user": values.get("user id") or values.get("user") or values.get("uid") or "root",
        "password": values.get("password") or values.get("pwd") or "",
        "database": values.get("database") or values.get("initial catalog") or "",
        "connect_timeout": 30,
        "charset": "utf8mb4",
        "autocommit": True,
        "cursorclass": pymysql.cursors.DictCursor,
    }


def get_config_error():
    host = os.environ.get("MySqlHost", "").strip()
    if not host:
        return None

    placeholders = {"YOUR_WINDOWS_IP", "YOUR_SERVER"}
    if host.upper() in placeholders:
        return f"MySqlHost is still '{host}'. Replace it with your MySQL host or leave it blank to use SqlConnectionString."

    return None


def open_mysql_connection():
    args = get_connection_args()
    if args is None:
        raise RuntimeError("SqlConnectionString is not configured.")
    return pymysql.connect(**args)


class SchemaProvider:
    def __init__(self):
        self._cached_customers_table = None

    def get_customers_table_name(self):
        if self._cached_customers_table:
            return self._cached_customers_table

        if get_connection_args() is None:
            return None

        sql = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND COLUMN_NAME IN ('Surname', 'CreditScore', 'CustomerId')
            GROUP BY TABLE_NAME
            HAVING SUM(COLUMN_NAME = 'Surname') > 0
            ORDER BY TABLE_NAME
            LIMIT 1
        """

        try:
            with open_mysql_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                    row = cursor.fetchone()
                    self._cached_customers_table = row["TABLE_NAME"] if row else None
                    return self._cached_customers_table
        except Exception:
            return None

    def list_tables(self):
        if get_connection_args() is None:
            return []

        sql = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """

        tables = []
        with open_mysql_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                for row in cursor.fetchall():
                    tables.append(row["TABLE_NAME"])
        return tables

    def get_schema_text(self):
        file_schema = self._load_schema_file()
        live_table = self.get_customers_table_name()

        if file_schema and live_table:
            return file_schema.replace("Customers", live_table)

        if file_schema:
            return file_schema

        return self._load_schema_from_database()

    @staticmethod
    def _load_schema_file():
        content = load_text_file("schema.sql").strip()
        return content if "CREATE TABLE" in content.upper() else ""

    @staticmethod
    def _load_schema_from_database():
        if get_connection_args() is None:
            return "-- No schema file and SqlConnectionString is not configured."

        sql = """
            SELECT
                c.TABLE_NAME,
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS c
            INNER JOIN INFORMATION_SCHEMA.TABLES t
                ON c.TABLE_SCHEMA = t.TABLE_SCHEMA
               AND c.TABLE_NAME = t.TABLE_NAME
            WHERE t.TABLE_TYPE = 'BASE TABLE'
              AND c.TABLE_SCHEMA = DATABASE()
            ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
        """

        lines = ["-- Auto-generated from INFORMATION_SCHEMA"]
        current_table = None
        with open_mysql_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                for row in cursor.fetchall():
                    table = row.get("TABLE_NAME", "")
                    column = row.get("COLUMN_NAME", "")
                    data_type = row.get("DATA_TYPE", "")
                    nullable = row.get("IS_NULLABLE", "")

                    if table != current_table:
                        if current_table is not None:
                            lines.append(");")
                        lines.append(f"CREATE TABLE `{table}` (")
                        current_table = table

                    lines.append(f"  `{column}` {data_type} NULL={nullable},")

        if current_table is not None:
            lines.append(");")

        return "\n".join(lines)


schema_provider = SchemaProvider()


MULTI_PART_PATTERN = re.compile(
    r"\b(and|also|plus|as\s+well\s+as)\b"
    r"|\?[^?]*\?"
    r"|,\s*(how|what|who|where|when|why|show|give|tell|list|count|average|total)",
    re.IGNORECASE,
)

CHART_PATTERN = re.compile(
    r"\b(graph|graphs|chart|charts|plot|plots|visual|visuali[sz]e|diagram|"
    r"pie\s*chart|bar\s*chart|line\s*chart|show\s+me\s+a\s+(graph|chart|plot))\b",
    re.IGNORECASE,
)

COMPARISON_PATTERN = re.compile(
    r"\b(or|vs|versus|compare|between|compared\s+to)\b",
    re.IGNORECASE,
)

ID_COLUMNS = {"customerid", "rownumber", "id"}
CATEGORY_COLUMNS = {"geography", "gender", "surname"}


def is_multi_part(question):
    return bool(question and MULTI_PART_PATTERN.search(question))


def enhance_for_sql(question):
    if not is_multi_part(question):
        return question

    return (
        question
        + "\n\nIMPORTANT: This message asks MULTIPLE things at once. "
        + "Return exactly ONE SELECT statement (no semicolons) that answers EVERY part. "
        + "Combine results using multiple columns, aggregates, CASE/SUM, and subqueries in the same query."
    )


def enhance_for_answer(question):
    if not is_multi_part(question):
        return question

    return (
        question
        + "\n\nIMPORTANT: Answer every part in 1-2 short lines total. Be terse."
    )


def parse_chat_request(data):
    if not isinstance(data, dict):
        data = {}

    message = str(data.get("message") or "")
    confirmed_surname = data.get("confirmed_surname")
    confirmed_customer_id = data.get("confirmed_customer_id")

    history = []
    raw_history = data.get("history")
    if isinstance(raw_history, list):
        for item in raw_history:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip()
            content = str(item.get("content") or "").strip()
            if role and content:
                history.append({"role": role, "content": content})

    return (
        message,
        history,
        str(confirmed_surname) if confirmed_surname else None,
        str(confirmed_customer_id) if confirmed_customer_id else None,
    )


def format_for_prompt(question, history, confirmed_surname=None, confirmed_customer_id=None):
    lines = []
    if history:
        lines.append("Conversation so far:")
        for item in history[-8:]:
            speaker = "User" if item["role"].lower() == "user" else "Assistant"
            lines.append(f"{speaker}: {item['content']}")

    lines.append(f"Current question: {question}" if lines else question)

    if confirmed_customer_id:
        lines.append(
            f"The user confirmed they mean CustomerId exactly: {confirmed_customer_id}. "
            "Use WHERE CustomerId = that exact value."
        )
    elif confirmed_surname:
        lines.append(
            f"The user confirmed they mean customer with Surname exactly: {confirmed_surname}. "
            "Use WHERE Surname = that exact value (not LIKE)."
        )

    return "\n".join(lines)


def get_openai_completion(system_prompt, user_prompt):
    api_key = os.environ.get("OpenAIApiKey")
    if not api_key or not api_key.strip():
        raise RuntimeError("OpenAIApiKey is not set in local.settings.json.")

    model = os.environ.get("OpenAIModel") or "gpt-4o-mini"
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=90,
    )

    body = response.text
    if not response.ok:
        try:
            message = response.json().get("error", {}).get("message") or body
        except ValueError:
            message = body
        raise RuntimeError(f"OpenAI request failed: {message}")

    payload = response.json()
    return payload["choices"][0]["message"].get("content") or ""


def extract_sql_query(raw):
    raw = (
        raw.replace("```json", "")
        .replace("```JSON", "")
        .replace("```sql", "")
        .replace("```SQL", "")
        .replace("```", "")
        .strip()
    )

    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            for key in ("query", "Query", "sql", "SQL"):
                value = payload.get(key)
                if value is not None:
                    return str(value)
    except ValueError:
        pass

    match = re.search(r"\bSELECT\b[\s\S]+", raw, re.IGNORECASE)
    if match:
        return match.group(0).strip().rstrip(";")

    return raw


def clean_sql(sql, actual_table_name="Customers"):
    if not sql or not sql.strip():
        return "NA"

    sql = (
        sql.replace("```json", "")
        .replace("```JSON", "")
        .replace("```sql", "")
        .replace("```SQL", "")
        .replace("```", "")
        .strip()
        .rstrip(";")
    )
    return fix_surname_prefix_match(fix_customers_schema(sql, actual_table_name))


def fix_surname_prefix_match(sql):
    sql = re.sub(
        r"(\bSurname\b)\s+LIKE\s+(['\"])%([^'\"%]+)%\2",
        r"\1 LIKE \2\3%\2",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"(\bSurname\b)\s+LIKE\s+(['\"])%([^'\"%]+)\2",
        r"\1 LIKE \2\3%\2",
        sql,
        flags=re.IGNORECASE,
    )
    return sql


def fix_customers_schema(sql, actual_table_name):
    table_name = actual_table_name or "Customers"

    sql = re.sub(
        r"(`?)(?:bank_data\.)?customers(`?)",
        lambda match: f"{match.group(1)}{table_name}{match.group(2)}",
        sql,
        flags=re.IGNORECASE,
    )

    columns = {
        "customerid": "CustomerId",
        "surname": "Surname",
        "creditscore": "CreditScore",
        "geography": "Geography",
        "gender": "Gender",
        "age": "Age",
        "tenure": "Tenure",
        "balance": "Balance",
        "numofproducts": "NumOfProducts",
        "hascrcard": "HasCrCard",
        "isactivemember": "IsActiveMember",
        "estimatedsalary": "EstimatedSalary",
        "exited": "Exited",
        "rownumber": "RowNumber",
    }

    for pattern, replacement in columns.items():
        sql = re.sub(rf"\b{pattern}\b", replacement, sql, flags=re.IGNORECASE)

    return sql


def strip_comments(sql):
    sql = re.sub(r"--[^\r\n]*", "", sql)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql.strip()


def validate_select_query(sql):
    if not sql or not sql.strip():
        return False, "Query is empty."

    stripped = strip_comments(sql.strip().rstrip(";"))
    if ";" in stripped:
        return False, "Multiple SQL statements are not allowed."

    for keyword in (
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        "EXEC",
        "EXECUTE",
        "MERGE",
        "GRANT",
        "REVOKE",
    ):
        if re.search(rf"\b{keyword}\b", stripped, re.IGNORECASE):
            return False, f"Blocked keyword detected: {keyword}."

    if re.search(r"\bSELECT\b[\s\S]+\bINTO\b", stripped, re.IGNORECASE):
        return False, "SELECT INTO is not allowed."

    if stripped.upper().startswith("SELECT"):
        return True, ""

    if stripped.upper().startswith("WITH") and re.search(r"\bSELECT\b", stripped, re.IGNORECASE):
        return True, ""

    return False, "Only read-only SELECT queries are allowed."


def make_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return int.from_bytes(value, byteorder="big") if len(value) <= 8 else value.hex()
    return value


def execute_sql(sql_query):
    results = []
    with open_mysql_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            for row in cursor.fetchmany(MAX_ROWS):
                results.append({key: make_json_value(value) for key, value in row.items()})
    return results


def get_candidates(results):
    if not results:
        return []

    keys = [key for row in results for key in row.keys()]
    surname_key = next((key for key in keys if key.lower() == "surname"), None)
    if not surname_key:
        return []

    customer_id_key = next((key for key in keys if key.lower() == "customerid"), None)
    seen = set()
    candidates = []

    for row in results:
        surname = row.get(surname_key)
        if not surname:
            continue

        customer_id = row.get(customer_id_key) if customer_id_key else None
        dedupe_key = str(customer_id) if customer_id is not None else str(surname).lower()
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        candidates.append({"customer_id": customer_id, "surname": str(surname)})

    return sorted(candidates, key=lambda c: (c["surname"].lower(), str(c["customer_id"])))


def should_confirm(candidates, question, confirmed_customer_id):
    if confirmed_customer_id:
        return False
    if len(candidates) <= 1:
        return False
    if COMPARISON_PATTERN.search(question or ""):
        return False
    return True


def wants_chart(question):
    return bool(question and CHART_PATTERN.search(question))


def is_numeric(value):
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, (int, float, Decimal)):
        return True
    try:
        float(str(value))
        return True
    except ValueError:
        return False


def get_numeric_columns(row):
    return [
        key
        for key, value in row.items()
        if key.lower() not in ID_COLUMNS and is_numeric(value)
    ]


def find_label_column(row):
    for key in row.keys():
        if key.lower() in CATEGORY_COLUMNS:
            return key

    for key, value in row.items():
        if key.lower() not in ID_COLUMNS and isinstance(value, str):
            return key

    return None


def recommend_chart(data, llm_chart_type, question):
    if not wants_chart(question) or not data:
        return "table"

    first = data[0]
    numeric_cols = get_numeric_columns(first)
    label_col = find_label_column(first)

    if len(data) == 1:
        if len(numeric_cols) >= 2 and label_col is None:
            parts_cols = [col.lower() for col in numeric_cols]
            wants_parts = any(
                "count" in col or "male" in col or "female" in col or "total" in col
                for col in parts_cols
            )
            return "pie" if wants_parts and len(numeric_cols) <= 6 else "bar"
        return "table"

    if label_col and numeric_cols:
        if len(data) <= 6 and label_col.lower() in CATEGORY_COLUMNS:
            return "pie"
        if len(data) <= 25:
            return "bar"

    if llm_chart_type in {"bar", "line", "pie", "table"}:
        return llm_chart_type

    if len(data) >= 2 and numeric_cols:
        return "bar"

    return "table"


def generate_sql(question, history, customers_table, confirmed_surname, confirmed_customer_id):
    schema_text = schema_provider.get_schema_text()
    instructions_text = load_text_file("instructions.txt")
    samples_text = load_text_file("sample_queries.txt")
    enhanced_question = enhance_for_sql(question)
    prompt_question = format_for_prompt(
        enhanced_question,
        history,
        confirmed_surname,
        confirmed_customer_id,
    )

    raw = get_openai_completion(
        system_prompt=f"{instructions_text}\n\nDatabase Schema:\n{schema_text}\n\nExample Queries:\n{samples_text}",
        user_prompt=prompt_question,
    )
    return extract_sql_query(raw)


def generate_answer(question, history, results, confirmed_surname, confirmed_customer_id):
    enhanced_question = enhance_for_answer(question)
    prompt_question = format_for_prompt(
        enhanced_question,
        history,
        confirmed_surname,
        confirmed_customer_id,
    )
    raw_answer = get_openai_completion(
        system_prompt=(
            "You are a helpful data analyst. Summarize query results as a clear, "
            "concise answer. Include notable insights. Your response will be shown "
            "in a web chat interface."
        ),
        user_prompt=f"{prompt_question}\n\nData: {json.dumps(results, default=str)}",
    )
    return raw_answer, recommend_chart(results, "table", question)


@app.route("/api/Chat", methods=["GET"])
def chat():
    path = BASE_DIR / "chat.html"
    if not path.exists():
        return "<h1>chat.html not found</h1>", 404
    return send_file(path, mimetype="text/html")


@app.route("/api/GetDatabaseSchema", methods=["GET"])
def get_database_schema():
    try:
        return jsonify(
            {
                "success": True,
                "schema": schema_provider.get_schema_text(),
                "hint": "Copy useful parts into schema.sql and sample_queries.txt for better answers.",
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)})


@app.route("/api/TestSqlConnection", methods=["GET", "POST"])
def test_sql_connection():
    if get_connection_args() is None:
        return jsonify(
            {
                "success": False,
                "message": "SqlConnectionString is not set in local.settings.json (Values section).",
            }
        )

    config_error = get_config_error()
    if config_error:
        return jsonify(
            {
                "success": False,
                "message": "Database config needs to be updated.",
                "error": config_error,
            }
        )

    try:
        with open_mysql_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION() AS ServerVersion, DATABASE() AS DatabaseName")
                row = cursor.fetchone() or {}

        args = get_connection_args() or {}
        return jsonify(
            {
                "success": True,
                "message": "Connected to MySQL successfully.",
                "server": args.get("host", ""),
                "database": row.get("DatabaseName", ""),
                "serverVersion": row.get("ServerVersion", ""),
            }
        )
    except Exception as exc:
        return jsonify(
            {
                "success": False,
                "message": "Failed to connect to MySQL.",
                "error": str(exc),
                "hint": "Connection refused usually means: wrong MySqlHost, MySQL not allowing remote connections, or a firewall blocking port 3306.",
            }
        )


@app.route("/api/AskQuestion", methods=["POST"])
def ask_question():
    payload = request.get_json(silent=True) or {}
    question, history, confirmed_surname, confirmed_customer_id = parse_chat_request(payload)

    if not question.strip():
        return jsonify({"error": 'Send JSON like { "message": "your question", "history": [] }.'})

    if get_connection_args() is None:
        return jsonify({"error": "SqlConnectionString is not configured."})

    if not os.environ.get("OpenAIApiKey"):
        return jsonify(
            {
                "answer": "Chat is not set up yet. Add your OpenAI API key to local.settings.json when you're ready."
            }
        )

    try:
        customers_table = schema_provider.get_customers_table_name()
        if not customers_table:
            tables = schema_provider.list_tables()
            return jsonify(
                {
                    "answer": "I can't find a Customers table in bank_data. Create/import your data first, then try again.",
                    "error": "No tables found in bank_data."
                    if not tables
                    else f"Tables found: {', '.join(tables)}",
                }
            )

        sql_query = generate_sql(
            question,
            history,
            customers_table,
            confirmed_surname,
            confirmed_customer_id,
        )
        sql_query = clean_sql(sql_query, customers_table)

        if sql_query.upper() == "NA":
            return jsonify(
                {
                    "query": "NA",
                    "answer": (
                        "I couldn't map that question to your bank_data tables. Open "
                        '/api/GetDatabaseSchema to see table and column names, then ask using those names - '
                        'for example: "What is the credit score for customers named Hill?"'
                    ),
                    "data": [],
                    "chart_type": "table",
                }
            )

        is_valid, validation_error = validate_select_query(sql_query)
        if not is_valid:
            return jsonify(
                {
                    "query": sql_query,
                    "answer": f"Query blocked for safety: {validation_error}",
                    "data": [],
                    "chart_type": "table",
                }
            )

        results = execute_sql(sql_query)
        candidates = get_candidates(results)
        if should_confirm(candidates, question, confirmed_customer_id):
            return jsonify(
                {
                    "query": sql_query,
                    "answer": f"I found {len(candidates)} matching customers. Which one did you mean?",
                    "needs_confirmation": True,
                    "candidates": candidates,
                    "data": results,
                    "chart_type": "table",
                }
            )

        answer, chart_type = generate_answer(
            question,
            history,
            results,
            confirmed_surname,
            confirmed_customer_id,
        )
        chart_type = recommend_chart(results, chart_type, question)

        return jsonify(
            {
                "query": sql_query,
                "answer": answer,
                "data": results,
                "chart_type": chart_type,
            }
        )
    except pymysql.MySQLError as exc:
        return jsonify(
            {
                "answer": "I couldn't run the database query. The table or column name may be wrong for your bank_data database.",
                "error": str(exc),
            }
        )
    except Exception as exc:
        message = str(exc)
        return jsonify(
            {
                "error": message,
                "answer": "ChatGPT request failed. Check your API key, billing, and restart the app after updating local.settings.json."
                if "OpenAI" in message
                else f"Something went wrong: {message}",
            }
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7179"))
    print(f"Starting IRI Chatbot on http://localhost:{port}/api/Chat")
    app.run(host="127.0.0.1", port=port, debug=False)
