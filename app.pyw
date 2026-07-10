import json
import os
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_file

try:
    import pyodbc
except Exception as exc:
    pyodbc = None
    PYODBC_IMPORT_ERROR = exc
else:
    PYODBC_IMPORT_ERROR = None

DATABASE_ERROR_TYPES = (pyodbc.Error,) if pyodbc is not None else ()


BASE_DIR = Path(__file__).resolve().parent
MEMORY_ROWS = 500
LOCAL_SETTINGS_CANDIDATES = [
    BASE_DIR / "local.settings.json",
    Path.cwd() / "local.settings.json",
]
LOCAL_SETTINGS_PATH = LOCAL_SETTINGS_CANDIDATES[0]
LOADED_SETTINGS_PATH = None
LOCAL_SETTINGS_ERROR = None
LOCAL_SETTINGS_WARNINGS = []

app = Flask(__name__)


def set_env_if_missing(name, value):
    if value is None:
        return

    current = os.environ.get(name)
    if current is None or not current.strip():
        os.environ[name] = str(value)


def read_settings_file(path):
    encodings = ("utf-8-sig", "utf-16")
    last_error = None
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding) as handle:
                return json.load(handle)
        except UnicodeError as exc:
            last_error = exc
        except json.JSONDecodeError as exc:
            last_error = exc
            break

    raise last_error or RuntimeError("Could not read settings file.")


def collect_settings_values(settings):
    values = {}
    if not isinstance(settings, dict):
        return values

    for section_name in ("Values", "ConnectionStrings"):
        section = settings.get(section_name)
        if isinstance(section, dict):
            values.update(section)

    for key in (
        "SqlConnectionString",
        "SQLCONNSTR_SqlConnectionString",
        "CUSTOMCONNSTR_SqlConnectionString",
        "ConnectionStrings:SqlConnectionString",
        "SqlServerHost",
        "OpenAIApiKey",
        "OpenAIModel",
    ):
        if key in settings:
            values[key] = settings[key]

    return values


def load_local_settings():
    global LOADED_SETTINGS_PATH, LOCAL_SETTINGS_ERROR
    seen = set()
    paths = []
    for path in LOCAL_SETTINGS_CANDIDATES:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            paths.append(resolved)

    path = next((candidate for candidate in paths if candidate.exists()), None)
    if path is None:
        LOCAL_SETTINGS_WARNINGS.append(
            "local.settings.json was not found in: "
            + ", ".join(str(candidate) for candidate in paths)
        )
        return

    try:
        settings = read_settings_file(path)
    except Exception as exc:
        LOCAL_SETTINGS_ERROR = str(exc)
        return

    LOADED_SETTINGS_PATH = path
    values = collect_settings_values(settings)

    aliases = {
        "SQLCONNSTR_SqlConnectionString": "SqlConnectionString",
        "CUSTOMCONNSTR_SqlConnectionString": "SqlConnectionString",
        "ConnectionStrings:SqlConnectionString": "SqlConnectionString",
    }
    for name, value in values.items():
        set_env_if_missing(aliases.get(name, name), value)


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


def get_connection_string():
    connection_string = (
        os.environ.get("SqlConnectionString")
        or os.environ.get("SQLCONNSTR_SqlConnectionString")
        or os.environ.get("CUSTOMCONNSTR_SqlConnectionString")
        or os.environ.get("ConnectionStrings:SqlConnectionString")
    )
    if not connection_string or not connection_string.strip():
        return None

    values = parse_connection_string(connection_string)
    host_override = os.environ.get("SqlServerHost", "").strip()

    if host_override:
        values["server"] = host_override

    if "driver" not in values:
        values["driver"] = "ODBC Driver 18 for SQL Server"
    if "trustservercertificate" not in values and "encrypt" not in values:
        values["trustservercertificate"] = "yes"

    ordered_keys = [
        "driver",
        "server",
        "database",
        "initial catalog",
        "user id",
        "uid",
        "password",
        "pwd",
        "trusted_connection",
        "integrated security",
        "encrypt",
        "trustservercertificate",
    ]
    parts = []
    seen = set()
    for key in ordered_keys:
        if key in values and values[key]:
            parts.append(f"{key}={values[key]}")
            seen.add(key)
    for key, value in values.items():
        if key not in seen and value:
            parts.append(f"{key}={value}")
    return ";".join(parts)


def get_settings_status():
    checked_paths = []
    seen = set()
    for path in LOCAL_SETTINGS_CANDIDATES:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            checked_paths.append(str(resolved))

    return {
        "settingsPath": str(LOADED_SETTINGS_PATH or LOCAL_SETTINGS_PATH),
        "checkedSettingsPaths": checked_paths,
        "settingsFileExists": bool(LOADED_SETTINGS_PATH),
        "settingsLoadError": LOCAL_SETTINGS_ERROR,
        "settingsWarnings": LOCAL_SETTINGS_WARNINGS,
        "hasSqlConnectionString": bool(get_connection_string()),
        "hasOpenAIApiKey": bool(os.environ.get("OpenAIApiKey", "").strip()),
    }


def get_config_error():
    host = os.environ.get("SqlServerHost", "").strip()
    placeholders = {"YOUR_WINDOWS_IP", "YOUR_SERVER"}
    if host and host.upper() in placeholders:
        return f"SqlServerHost is still '{host}'. Replace it with your SQL Server host or leave it blank to use SqlConnectionString."

    values = parse_connection_string(get_connection_string() or "")
    configured_server = values.get("server", "").split(",", 1)[0].strip()
    if configured_server.upper() in placeholders:
        return "SqlConnectionString still contains YOUR_SERVER. Replace the placeholders in local.settings.json with your SQL Server details."

    return None


def print_startup_config():
    status = get_settings_status()
    print(f"App file: {Path(__file__).resolve()}")
    print("Settings paths checked:")
    for path in status["checkedSettingsPaths"]:
        print(f"  - {path}")
    print(f"Settings file loaded: {status['settingsFileExists']}")
    print(f"Settings path used: {status['settingsPath']}")
    if status["settingsLoadError"]:
        print(f"Settings load error: {status['settingsLoadError']}")
    for warning in status["settingsWarnings"]:
        print(f"Settings warning: {warning}")
    print(f"SqlConnectionString loaded: {status['hasSqlConnectionString']}")
    print(f"OpenAIApiKey loaded: {status['hasOpenAIApiKey']}")


def open_sql_server_connection():
    if pyodbc is None:
        raise RuntimeError(
            "pyodbc could not load. Install pyodbc and Microsoft ODBC Driver 18 for SQL Server, "
            f"then restart the app. Details: {PYODBC_IMPORT_ERROR}"
        )

    connection_string = get_connection_string()
    if connection_string is None:
        raise RuntimeError("SqlConnectionString is not configured.")
    return pyodbc.connect(connection_string, timeout=30, autocommit=True)


def rows_as_dicts(cursor):
    columns = [column[0] for column in cursor.description or []]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


class SchemaProvider:
    def __init__(self):
        self._cached_schema_text = None

    def list_tables(self):
        if get_connection_string() is None:
            return []

        sql = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_CATALOG = DB_NAME()
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """

        tables = []
        with open_sql_server_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                for row in rows_as_dicts(cursor):
                    tables.append(row["TABLE_NAME"])
        return tables

    def get_schema_text(self):
        if self._cached_schema_text:
            return self._cached_schema_text

        if get_connection_string() is not None:
            live_schema = self._load_schema_from_database()
            if "CREATE TABLE" in live_schema.upper():
                self._cached_schema_text = live_schema
                return live_schema

        return self._load_schema_from_database()

    @staticmethod
    def _load_schema_from_database():
        if get_connection_string() is None:
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
              AND c.TABLE_CATALOG = DB_NAME()
            ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
        """

        lines = ["-- Auto-generated from INFORMATION_SCHEMA"]
        current_table = None
        with open_sql_server_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                for row in rows_as_dicts(cursor):
                    table = row.get("TABLE_NAME", "")
                    column = row.get("COLUMN_NAME", "")
                    data_type = row.get("DATA_TYPE", "")
                    nullable = row.get("IS_NULLABLE", "")

                    if table != current_table:
                        if current_table is not None:
                            lines.append(");")
                        lines.append(f"CREATE TABLE [{table}] (")
                        current_table = table

                    lines.append(f"  [{column}] {data_type} NULL={nullable},")

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
LISTING_PATTERN = re.compile(
    r"\b(top|bottom|first|last|highest|lowest|most|least|all|list|show|give|"
    r"rank|ranking|sort|order|rows|records|results)\b",
    re.IGNORECASE,
)

ID_COLUMNS = {"id"}
CATEGORY_COLUMNS = {
    "category",
    "type",
    "status",
    "region",
    "country",
    "state",
    "city",
    "name",
    "label",
    "title",
}
VALID_CHART_TYPES = {"bar", "line", "pie"}


def normalize_column_name(name):
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def is_id_column_name(name):
    normalized = normalize_column_name(name)
    return normalized == "id" or normalized.endswith("id")


def is_label_column_name(name):
    normalized = normalize_column_name(name)
    return (
        normalized in {"name", "label", "title", "email", "username"}
        or normalized.endswith("name")
        or normalized.endswith("label")
        or normalized.endswith("title")
    )


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
    confirmed_label = data.get("confirmed_label")
    confirmed_id = data.get("confirmed_id")

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
        str(confirmed_label) if confirmed_label else None,
        str(confirmed_id) if confirmed_id else None,
    )


def format_for_prompt(question, history, confirmed_label=None, confirmed_id=None):
    lines = []
    if history:
        lines.append("Conversation so far:")
        for item in history[-8:]:
            speaker = "User" if item["role"].lower() == "user" else "Assistant"
            lines.append(f"{speaker}: {item['content']}")

    lines.append(f"Current question: {question}" if lines else question)

    if confirmed_id:
        lines.append(
            f"The user selected the result/entity whose id is exactly: {confirmed_id}. "
            "Use the relevant id column from the schema if that resolves the question."
        )
    elif confirmed_label:
        lines.append(
            f"The user selected the result/entity labeled exactly: {confirmed_label}. "
            "Use the relevant name/label column from the schema if that resolves the question."
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


def clean_sql(sql):
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
    return convert_limit_to_top(sql)


def convert_limit_to_top(sql):
    match = re.search(r"\s+LIMIT\s+(\d+)\s*$", sql, re.IGNORECASE)
    if not match:
        return sql

    limit = match.group(1)
    without_limit = sql[: match.start()].rstrip()
    if re.match(r"^\s*SELECT\s+TOP\s*\(", without_limit, re.IGNORECASE):
        return without_limit
    if re.match(r"^\s*SELECT\s+DISTINCT\b", without_limit, re.IGNORECASE):
        return re.sub(
            r"^\s*SELECT\s+DISTINCT\b",
            f"SELECT DISTINCT TOP ({limit})",
            without_limit,
            count=1,
            flags=re.IGNORECASE,
        )
    return re.sub(
        r"^\s*SELECT\b",
        f"SELECT TOP ({limit})",
        without_limit,
        count=1,
        flags=re.IGNORECASE,
    )


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
    with open_sql_server_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            for row in rows_as_dicts(cursor):
                results.append({key: make_json_value(value) for key, value in row.items()})
    return results


def user_requested_specific_row_count(question):
    text = question or ""
    if re.search(r"\b(top|bottom|first|last)\s+\d+\b", text, re.IGNORECASE):
        return True
    if re.search(r"\b\d+\s+(rows|records|results)\b", text, re.IGNORECASE):
        return True
    if re.search(r"\blimit\s+\d+\b", text, re.IGNORECASE):
        return True
    return False


def remove_broad_query_limit(sql_query, question):
    if user_requested_specific_row_count(question):
        return sql_query

    if not LISTING_PATTERN.search(question or ""):
        return sql_query

    pattern = re.compile(r"\bLIMIT\s+(\d+)\s*$", re.IGNORECASE)
    match = pattern.search(sql_query)
    if match:
        return pattern.sub("", sql_query).rstrip()

    top_pattern = re.compile(r"^\s*SELECT\s+(DISTINCT\s+)?TOP\s*\(\s*\d+\s*\)\s+", re.IGNORECASE)
    return top_pattern.sub(lambda match: f"SELECT {match.group(1) or ''}", sql_query, count=1)


def find_first_column(keys, matcher):
    for key in keys:
        if matcher(key):
            return key
    return None


def get_candidates(results):
    if not results:
        return []

    keys = [key for row in results for key in row.keys()]
    label_key = find_first_column(
        keys,
        is_label_column_name,
    )
    if not label_key:
        return []

    id_key = find_first_column(
        keys,
        is_id_column_name,
    )
    seen = set()
    candidates = []

    for row in results:
        label = row.get(label_key)
        if not label:
            continue

        entity_id = row.get(id_key) if id_key else None
        dedupe_key = str(entity_id) if entity_id is not None else str(label).lower()
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        candidates.append({"id": entity_id, "label": str(label)})

    return sorted(candidates, key=lambda c: (c["label"].lower(), str(c["id"])))


def should_confirm(candidates, question, confirmed_id):
    if confirmed_id:
        return False
    if len(candidates) <= 1:
        return False
    if COMPARISON_PATTERN.search(question or ""):
        return False
    if LISTING_PATTERN.search(question or ""):
        return False

    label_counts = {}
    for candidate in candidates:
        label = str(candidate.get("label") or "").strip().lower()
        if label:
            label_counts[label] = label_counts.get(label, 0) + 1

    duplicate_labels = [
        label
        for label, count in label_counts.items()
        if count > 1
    ]
    question_text = question or ""
    return any(
        re.search(rf"\b{re.escape(label)}\b", question_text, re.IGNORECASE)
        for label in duplicate_labels
    )


def wants_chart(question):
    return bool(question and CHART_PATTERN.search(question))


def requested_chart_type(question):
    text = (question or "").lower()
    if re.search(r"\bpie(?:\s+chart)?\b", text):
        return "pie"
    if re.search(r"\bline(?:\s+chart|\s+graph)?\b", text):
        return "line"
    if re.search(r"\bbar(?:\s+chart|\s+graph)?\b", text):
        return "bar"
    return None


def is_chart_followup(question):
    if not wants_chart(question) and requested_chart_type(question) is None:
        return False

    tokens = re.findall(r"[a-z0-9]+", (question or "").lower())
    filler = {
        "a",
        "an",
        "and",
        "as",
        "bar",
        "can",
        "chart",
        "charts",
        "diagram",
        "graph",
        "graphs",
        "it",
        "line",
        "make",
        "me",
        "now",
        "of",
        "ok",
        "okay",
        "people",
        "person",
        "pie",
        "please",
        "plot",
        "for",
        "result",
        "results",
        "show",
        "that",
        "the",
        "them",
        "these",
        "this",
        "those",
        "to",
        "turn",
        "visual",
        "visualize",
        "visualise",
        "you",
    }
    meaningful_tokens = [token for token in tokens if token not in filler]
    return len(meaningful_tokens) == 0


def parse_last_result(payload):
    last_result = payload.get("last_result") if isinstance(payload, dict) else None
    if not isinstance(last_result, dict):
        return None

    rows = last_result.get("data")
    if not isinstance(rows, list):
        rows = []

    clean_rows = []
    for row in rows[:MEMORY_ROWS]:
        if isinstance(row, dict):
            clean_rows.append(row)

    return {
        "question": str(last_result.get("question") or ""),
        "answer": str(last_result.get("answer") or ""),
        "query": str(last_result.get("query") or ""),
        "chart_type": str(last_result.get("chart_type") or "table"),
        "data": clean_rows,
        "memory": last_result.get("memory") if isinstance(last_result.get("memory"), dict) else {},
    }


def summarize_last_result(last_result):
    if not last_result or not last_result.get("data"):
        return ""

    rows = last_result["data"]
    columns = list(rows[0].keys()) if rows and isinstance(rows[0], dict) else []
    preview = rows[:5]
    parts = [
        "Previous result context:",
        f"Previous question: {last_result.get('question', '')}",
        f"Previous SQL query: {last_result.get('query', '')}",
        f"Previous columns: {', '.join(columns)}",
        f"Previous rows shown: {len(rows)}",
        f"First rows: {json.dumps(preview, default=str)}",
    ]

    memory = last_result.get("memory") if isinstance(last_result.get("memory"), dict) else {}
    entities = memory.get("entities") if isinstance(memory.get("entities"), list) else []
    if not entities:
        entities = memory.get("people") if isinstance(memory.get("people"), list) else []
    numeric_columns = memory.get("numeric_columns") if isinstance(memory.get("numeric_columns"), list) else []

    if entities:
        parts.append(
            "Previous entities/rows: "
            + json.dumps(entities[:20], default=str)
        )
    if memory.get("label_column"):
        parts.append(f"Previous chart label/x-axis column: {memory['label_column']}")
    if memory.get("value_column"):
        parts.append(f"Previous chart value/y-axis column: {memory['value_column']}")
    if numeric_columns:
        parts.append(f"Previous numeric metrics: {', '.join(str(col) for col in numeric_columns)}")
    if last_result.get("chart_type"):
        parts.append(f"Previous chart type: {last_result['chart_type']}")
    if entities:
        parts.append(
            "If the user says they, them, their, those, or those rows, "
            "treat that as referring to the previous entities/rows listed above."
        )

    return "\n".join(part for part in parts if part.strip())


def add_result_context_to_history(history, last_result):
    summary = summarize_last_result(last_result)
    if not summary:
        return history
    return [*history, {"role": "assistant", "content": summary}]


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
    explicit_chart_type = requested_chart_type(question)
    if not data or (not wants_chart(question) and explicit_chart_type is None):
        return "table"

    first = data[0]
    numeric_cols = get_numeric_columns(first)
    label_col = find_label_column(first)
    preferred_chart_type = explicit_chart_type
    if preferred_chart_type is None and llm_chart_type in VALID_CHART_TYPES:
        preferred_chart_type = llm_chart_type

    if preferred_chart_type is not None:
        return preferred_chart_type

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

    if len(data) >= 2 and numeric_cols:
        return "bar"

    return "table"


def build_chart_followup_response(question, last_result):
    if not last_result or not last_result.get("data"):
        return None

    rows = last_result["data"]
    chart_type = requested_chart_type(question) or recommend_chart(rows, last_result.get("chart_type"), question)
    if chart_type == "table":
        chart_type = recommend_chart(rows, "bar", "show me a chart")

    answer = (
        f"Here is a {chart_type} chart for the previous results."
        if chart_type != "table"
        else "I can show the previous results, but they do not have enough chartable values for a graph."
    )

    return {
        "query": last_result.get("query") or "",
        "answer": answer,
        "data": rows,
        "chart_type": chart_type,
        "chart_followup": True,
    }


def generate_sql(question, history, confirmed_label, confirmed_id):
    schema_text = schema_provider.get_schema_text()
    instructions_text = load_text_file("instructions.txt")
    enhanced_question = enhance_for_sql(question)
    prompt_question = format_for_prompt(
        enhanced_question,
        history,
        confirmed_label,
        confirmed_id,
    )

    raw = get_openai_completion(
        system_prompt=f"{instructions_text}\n\nDatabase Schema:\n{schema_text}",
        user_prompt=prompt_question,
    )
    return extract_sql_query(raw)


def generate_answer(question, history, results, confirmed_label, confirmed_id):
    enhanced_question = enhance_for_answer(question)
    if is_large_result_question(question, results):
        return build_compact_result_answer(question, results), recommend_chart(results, "table", question)

    prompt_question = format_for_prompt(
        enhanced_question,
        history,
        confirmed_label,
        confirmed_id,
    )
    raw_answer = get_openai_completion(
        system_prompt=(
            "You are a helpful data analyst. Summarize query results as a clear, "
            "concise answer. Include notable insights. Your response will be shown "
            "in a web chat interface. Do not list rows one by one, do not use markdown "
            "tables, and do not repeat every field from the data. The UI already shows "
            "the rows in a table/chart, so keep the answer to a few sentences."
        ),
        user_prompt=f"{prompt_question}\n\nData: {json.dumps(results, default=str)}",
    )
    return raw_answer, recommend_chart(results, "table", question)


def is_large_result_question(question, results):
    if len(results) >= 8:
        return True
    return bool(results and LISTING_PATTERN.search(question or ""))


def build_compact_result_answer(question, results):
    row_count = len(results)
    noun = "row" if row_count == 1 else "rows"

    if wants_chart(question) or requested_chart_type(question):
        return f"I found {row_count} matching {noun}."

    return f"I found {row_count} matching {noun}."


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
                "hint": "Use this schema when writing database-specific mappings in instructions.txt.",
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)})


@app.route("/api/TestSqlConnection", methods=["GET", "POST"])
def test_sql_connection():
    if get_connection_string() is None:
        return jsonify(
            {
                "success": False,
                "message": "SqlConnectionString is not loaded.",
                "error": (
                    "Check that local.settings.json is beside app.pyw and contains "
                    'Values.SqlConnectionString or ConnectionStrings.SqlConnectionString.'
                ),
                "config": get_settings_status(),
            }
        )

    config_error = get_config_error()
    if config_error:
        return jsonify(
            {
                "success": False,
                "message": "Database config needs to be updated.",
                "error": config_error,
                "config": get_settings_status(),
            }
        )

    try:
        with open_sql_server_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT @@VERSION AS ServerVersion, DB_NAME() AS DatabaseName")
                rows = rows_as_dicts(cursor)
                row = rows[0] if rows else {}

        values = parse_connection_string(get_connection_string() or "")
        return jsonify(
            {
                "success": True,
                "message": "Connected to SQL Server successfully.",
                "server": os.environ.get("SqlServerHost", "").strip()
                or values.get("server", "")
                or values.get("data source", ""),
                "database": row.get("DatabaseName", ""),
                "serverVersion": row.get("ServerVersion", ""),
                "config": get_settings_status(),
            }
        )
    except Exception as exc:
        return jsonify(
            {
                "success": False,
                "message": "Failed to connect to SQL Server.",
                "error": str(exc),
                "hint": "Connection refused usually means: wrong SqlServerHost/server, SQL Server not allowing TCP connections, missing ODBC Driver 18, or a firewall blocking port 1433.",
                "config": get_settings_status(),
            }
        )


@app.route("/api/AskQuestion", methods=["POST"])
def ask_question():
    payload = request.get_json(silent=True) or {}
    question, history, confirmed_label, confirmed_id = parse_chat_request(payload)
    last_result = parse_last_result(payload)

    if not question.strip():
        return jsonify({"error": 'Send JSON like { "message": "your question", "history": [] }.'})

    if is_chart_followup(question):
        chart_response = build_chart_followup_response(question, last_result)
        if chart_response is not None:
            return jsonify(chart_response)

    if get_connection_string() is None:
        return jsonify(
            {
                "error": "SqlConnectionString is not configured.",
                "config": get_settings_status(),
            }
        )

    if not os.environ.get("OpenAIApiKey"):
        return jsonify(
            {
                "answer": "Chat is not set up yet. Add your OpenAI API key to local.settings.json when you're ready."
            }
        )

    try:
        history = add_result_context_to_history(history, last_result)
        tables = schema_provider.list_tables()
        if not tables:
            return jsonify(
                {
                    "answer": "I can't find any tables in the connected database. Create/import your data first, then try again.",
                    "error": "No base tables found in the connected database.",
                }
            )

        sql_query = generate_sql(
            question,
            history,
            confirmed_label,
            confirmed_id,
        )
        sql_query = clean_sql(sql_query)
        sql_query = remove_broad_query_limit(sql_query, question)

        if sql_query.upper() == "NA":
            return jsonify(
                {
                    "query": "NA",
                    "answer": (
                        "I couldn't map that question to your database tables. Open "
                        '/api/GetDatabaseSchema to see table and column names, then ask using those names - '
                        'for example: "How many rows are in TableName?"'
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
        if should_confirm(candidates, question, confirmed_id):
            return jsonify(
                {
                    "query": sql_query,
                    "answer": f"I found {len(candidates)} matching results. Which one did you mean?",
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
            confirmed_label,
            confirmed_id,
        )
        chart_type = recommend_chart(results, chart_type, question)

        return jsonify(
            {
                "query": sql_query,
                "answer": answer,
                "data": results,
                "chart_type": chart_type,
                "total_rows": len(results),
            }
        )
    except DATABASE_ERROR_TYPES as exc:
        return jsonify(
            {
                "answer": "I couldn't run the database query. The table or column name may be wrong for your connected database.",
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
    host = os.environ.get("HOST", "0.0.0.0")
    print_startup_config()
    print(f"Starting IRI AI on http://localhost:{port}/api/Chat")
    app.run(host=host, port=port, debug=False)
