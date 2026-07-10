# IRI AI Chatbot

Python Flask app (`app.pyw`) that talks to SQL Server and ChatGPT.

## Windows setup

1. Install Python 3 and select **Add Python to PATH** during installation.
2. Install **Microsoft ODBC Driver 18 for SQL Server**.
3. Copy `local.settings.example.json` to `local.settings.json` if you do not
   already have one.
4. `local.settings.json` is already filled in for SQL Server `Prohance`
   (`VMWinSQLS` / configured password) and the OpenAI key. You can copy from
   the example if needed:

```text
copy local.settings.example.json local.settings.json
```

Or double-click `setup_local_settings.bat` / `repair_settings.bat`.

`172.18.0.4` is often a Docker/internal IP. If the DB will not connect from your PC,
on the **SQL Server machine** run `ipconfig`, copy the Ethernet/Wi-Fi IPv4
(usually `192.168.x.x` or `10.x.x.x`), and put that in `SqlServer` instead.

When you start the app, the console should show `SQL settings loaded: True`,
`passwordSet=True`, and `SQL target: server=172.18.0.4,1433`. If it shows
`False` / `(missing)`, the settings file next to `app.pyw` is wrong or not saved.

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

- **Login failed** — wrong `SqlUser` / `SqlPassword`, or that login cannot use `Prohance`.
  Re-run `repair_settings.bat` if an old folder still has `YOUR_PASSWORD`.
- **Could not open a connection / TCP Provider** — your PC cannot reach `172.18.0.4:1433`.
  On the SQL Server PC, enable TCP/IP, open firewall TCP 1433, allow remote SQL logins
  (mixed mode), and prefer the LAN IPv4 from `ipconfig` over `172.18.0.4`.
- **ODBC driver not found** — install ODBC Driver 18 for SQL Server on the chatbot PC.

## Configuration safety

`local.settings.json` is gitignored because it contains passwords and API keys.
Keep secrets only in that local file.

## Connection test

```text
http://localhost:7179/api/TestSqlConnection
```
