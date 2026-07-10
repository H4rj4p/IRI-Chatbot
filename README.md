# IRI AI Chatbot

Natural-language Q&A over a **SQL Server** `bank_data` database (Customers table).

## Prerequisites

- [.NET 8 SDK](https://dotnet.microsoft.com/download)
- Access to a SQL Server instance with your `bank_data` / Customers data
- An OpenAI API key

## Configure (fill these in yourself)

1. Copy the example settings file:

```bash
cp local.settings.example.json local.settings.json
```

2. Edit `local.settings.json` and replace the placeholders:

| Setting | What to put |
|---|---|
| `SqlConnectionString` | SQL Server host, database, username, password |
| `OpenAIApiKey` | Your OpenAI / GPT API key |
| `SqlServerHost` | Optional host override; leave blank to use `Server=` from the connection string |
| `OpenAIModel` | Defaults to `gpt-4o-mini` |

This project is configured for SQL Server `VMWinSQLS` / database `Prohance`. Replace `YOUR_USER`, `YOUR_PASSWORD`, and `YOUR_OPENAI_API_KEY` yourself.

SQL authentication example:

```text
Server=VMWinSQLS,1433;Database=Prohance;User ID=YOUR_USER;Password=YOUR_PASSWORD;Encrypt=True;TrustServerCertificate=True;
```

Windows authentication example:

```text
Server=VMWinSQLS;Database=Prohance;Integrated Security=True;Encrypt=True;TrustServerCertificate=True;
```

`local.settings.json` is gitignored so passwords and API keys stay private.

## Run locally

```bash
./run.sh
```

On Windows:

```bat
run.bat
```

Then open <http://localhost:7179/api/Chat>.

Connection test: <http://localhost:7179/api/TestSqlConnection>

## Deploy to Azure Functions

1. Create a Function App (`.NET 8` isolated worker).
2. Set application settings (or connection strings) on the Function App:

- `SqlConnectionString` — same SQL Server connection string as local
- `OpenAIApiKey` — your GPT key
- `OpenAIModel` — optional (`gpt-4o-mini`)
- `FUNCTIONS_WORKER_RUNTIME` — `dotnet-isolated`

3. Publish:

```bash
func azure functionapp publish YOUR_FUNCTION_APP_NAME
```

Or from Visual Studio / VS Code: publish the `IriChatbotFunction` project to the Function App.

After deploy, open `https://YOUR_FUNCTION_APP_NAME.azurewebsites.net/api/Chat`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/Chat` | Chat UI |
| POST | `/api/AskQuestion` | Ask a natural-language question |
| GET | `/api/GetDatabaseSchema` | Inspect live schema |
| GET/POST | `/api/TestSqlConnection` | Verify SQL Server connectivity |
