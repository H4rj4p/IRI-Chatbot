# IRI AI Chatbot

Python Flask app (`app.pyw`) that talks to SQL Server and ChatGPT.

## Windows setup

1. Install Python 3 and select **Add Python to PATH** during installation.
2. Install **Microsoft ODBC Driver 18 for SQL Server**.
3. Copy `local.settings.example.json` to `local.settings.json` if you do not
   already have one.
4. Edit `local.settings.json` and set your password:

```json
{
  "IsEncrypted": false,
  "Values": {
    "SqlServer": "VMWinSQLS,1433",
    "SqlDatabase": "Prohance",
    "SqlUser": "VMWinSQLS",
    "SqlPassword": "your-real-password",
    "OpenAIApiKey": "your-openai-key",
    "OpenAIModel": "gpt-4o-mini"
  }
}
```

If the chatbot runs on a different PC from SQL Server, keep
`"SqlServer": "VMWinSQLS,1433"`. If that hostname does not resolve on your PC,
use the SQL Server PC's IPv4 address instead, for example `"10.0.0.50,1433"`.

Do **not** use `localhost` unless the chatbot and SQL Server are on the same machine.

5. Install packages once:

```text
pip install -r requirements.txt
```

6. Run the app:

```text
python app.pyw
```

7. Open <http://localhost:7179/api/Chat>

If the page says the database is not connected, read the error/hint in the chat
window. After any settings change, stop the app with Ctrl+C and run
`python app.pyw` again.

## Common connection fixes

- **Password still placeholder** — replace `YOUR_PASSWORD` in `SqlPassword`.
- **Login failed** — wrong `SqlUser` / `SqlPassword`, or that login cannot use `Prohance`.
- **Could not open a connection / TCP Provider** — your PC cannot reach the SQL Server.
  Use the SQL Server hostname or IP (not localhost). On the SQL Server PC, enable TCP/IP,
  open firewall port 1433, and allow remote SQL logins (mixed mode).
- **ODBC driver not found** — install ODBC Driver 18 for SQL Server on the chatbot PC.

## Configuration safety

`local.settings.json` is gitignored because it contains passwords and API keys.
Keep secrets only in that local file.

## Connection test

```text
http://localhost:7179/api/TestSqlConnection
```
