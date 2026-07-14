# IRI AI Chatbot

Python Flask app (`app.pyw`) that talks to SQL Server (`Prohance`) and ChatGPT.

## Use from any phone / laptop / PC

The browser never talks to SQL Server directly. One PC near the database runs the
app; every other device just opens the chat URL.

1. On the **SQL Server PC**, double-click **`start_anywhere.bat`** and leave it open.
2. Wait until the console shows SQL connected (or run `python diagnose_sql.py`).
3. From **any device**:
   - Same Wi-Fi: open one of the printed `http://192.168.x.x:7179/api/Chat` links
   - Anywhere on the internet: install [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/),
     re-run `start_anywhere.bat`, and open the `https://....trycloudflare.com` URL

`local.settings.json` is already filled for Prohance. The app auto-tries
`127.0.0.1`, `localhost`, `host.docker.internal`, `172.18.0.4`, and `VMWinSQLS`,
then saves whichever host works.

## Windows setup (SQL Server PC)

1. Install Python 3 (**Add Python to PATH**).
2. Install **Microsoft ODBC Driver 18 for SQL Server**.
3. `pip install -r requirements.txt`
4. Double-click `start_anywhere.bat`

| Setting | Value |
| --- | --- |
| Primary SqlServer | `127.0.0.1,1433` |
| Alternates | `172.18.0.4`, `localhost`, `host.docker.internal`, `VMWinSQLS` |
| Database | `Prohance` |
| User | `VMWinSQLS` |

## Common connection fixes

- **Handshake / error 26 on 172.18.x.x** — run on the SQL PC; localhost is tried first.
- **Login failed** — check `SqlUser` / `SqlPassword` for database `Prohance`.
- **TCP / timeout** — enable SQL TCP 1433, firewall, SQL authentication.
- **ODBC driver not found** — install ODBC Driver 18.

## Manual commands

```text
python diagnose_sql.py
python app.pyw
```

- Chat: <http://localhost:7179/api/Chat>
- Test: <http://localhost:7179/api/TestSqlConnection>
- Access URLs: <http://localhost:7179/api/AccessInfo>
