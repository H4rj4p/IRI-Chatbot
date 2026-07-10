# IRI AI Chatbot

Python Flask app (`app.pyw`) that talks to SQL Server and ChatGPT.

## Windows setup

1. Install Python 3 and select **Add Python to PATH** during installation.
2. Install **Microsoft ODBC Driver 18 for SQL Server**.
3. Copy `local.settings.example.json` to `local.settings.json` if you do not
   already have one.
4. Edit `local.settings.json`. Server `VMWinSQLS`, database `Prohance`, and
   user `VMWinSQLS` are pre-filled — replace `YOUR_PASSWORD` (and the OpenAI
   API key if needed) with your real values.
5. Install packages once:

```text
pip install -r requirements.txt
```

6. Run the app:

```text
python app.pyw
```

Or double-click `start_iri_chatbot_7180.bat` (same thing; uses port 7180).

7. Open <http://localhost:7179/api/Chat> (or <http://localhost:7180/api/Chat>
   if you used the `.bat` launcher).

The page tests the SQL Server connection when it loads and shows the
configuration location and connection error if the test fails.

## SQL Server connection examples

SQL authentication:

```text
Driver={ODBC Driver 18 for SQL Server};Server=VMWinSQLS,1433;Database=Prohance;User ID=VMWinSQLS;Password=PASSWORD;Encrypt=yes;TrustServerCertificate=yes;
```

Windows authentication:

```text
Driver={ODBC Driver 18 for SQL Server};Server=SERVER_NAME;Database=DATABASE_NAME;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;
```

For a named SQL Server instance, use `Server=SERVER_NAME\\INSTANCE_NAME`.
SQL Server must allow TCP connections, and its configured port must be allowed
through the Windows firewall.

## Configuration safety

`local.settings.json` is intentionally excluded from Git because it contains
passwords and API keys. Commit `local.settings.example.json` as the configuration
template, and create a private `local.settings.json` on each computer.

## Connection test

With the app running, visit:

```text
http://localhost:7179/api/TestSqlConnection
```

A successful response includes `"success": true`, the connected database name,
and the SQL Server version.
