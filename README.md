# IRI AI Chatbot

Python Flask app (`app.pyw`) that talks to SQL Server (`Prohance`) and ChatGPT.

## Where to run it

SQL Server is currently configured as `172.18.0.4,1433`. That address only works
inside the SQL Server Docker/host network.

- **Best:** run the chatbot on the **same Windows PC / Docker host** as SQL Server,
  and set `SqlServer` to `127.0.0.1,1433`.
- **Another PC on the LAN:** on the SQL Server machine run `ipconfig`, copy the
  Ethernet/Wi-Fi IPv4 (usually `192.168.x.x` or `10.x.x.x`), and put that in
  `SqlServer` like `192.168.1.50,1433`.
- Cloud agents / tunnels **cannot** reach a private Docker IP like `172.18.0.4`.

## Windows setup

1. Install Python 3 and select **Add Python to PATH**.
2. Install **Microsoft ODBC Driver 18 for SQL Server**.
3. Create settings:

```text
copy local.settings.example.json local.settings.json
```

Or double-click `setup_local_settings.bat` / `repair_settings.bat`.

Configured defaults:

| Setting | Value |
| --- | --- |
| Server | `172.18.0.4,1433` (prefer `127.0.0.1,1433` on the SQL PC) |
| Database | `Prohance` |
| User | `VMWinSQLS` |
| Password | set in `local.settings.json` |

4. Install packages once:

```text
pip install -r requirements.txt
```

5. Diagnose the connection:

```text
python diagnose_sql.py
```

6. Start the app (either works):

```text
python app.pyw
```

or double-click `start_iri_chatbot.bat` (port **7179**) /
`start_iri_chatbot_7180.bat` (port **7180**).

7. Open the chat page and connection test:

- Chat: <http://localhost:7179/api/Chat>
- Test: <http://localhost:7179/api/TestSqlConnection>

On startup the console should show `SQL settings loaded: True`, `passwordSet=True`,
and the SQL target. If it shows `False` / `(missing)`, fix `local.settings.json`
beside `app.pyw`, then restart.

If `172.18.0.4` fails, the app also tries `127.0.0.1,1433` and `localhost,1433`
automatically. When a fallback works, update `SqlServer` permanently to that value.

## Common connection fixes

- **Handshake before login / error 26** — `172.18.x.x` is not reachable as SQL from
  this machine. Use `127.0.0.1,1433` on the SQL host, or the LAN IPv4 from another PC.
- **Login failed** — wrong `SqlUser` / `SqlPassword`, or that login cannot use `Prohance`.
- **Could not open a connection / TCP Provider** — enable TCP/IP, open firewall TCP 1433,
  allow SQL authentication (mixed mode).
- **ODBC driver not found** — install ODBC Driver 18 for SQL Server.

## Configuration safety

`local.settings.json` is gitignored because it contains passwords and API keys.
Commit only `local.settings.example.json` as the template. Keep secrets private.

## SQL authentication connection string

```text
Driver={ODBC Driver 18 for SQL Server};Server=127.0.0.1,1433;Database=Prohance;User ID=VMWinSQLS;Password=YOUR_PASSWORD;Encrypt=yes;TrustServerCertificate=yes;
```
