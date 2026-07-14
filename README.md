# IRI AI Chatbot

Python Flask chat UI for SQL Server (`Prohance`) + ChatGPT.

## Step 1 — see it on localhost (do this first)

1. Install Python 3 (**Add to PATH**) and **ODBC Driver 18 for SQL Server**.
2. In this folder:

```text
pip install -r requirements.txt
```

3. Double-click **`start_iri_chatbot.bat`** (or run `python app.pyw`).
4. Open **http://localhost:7179/api/Chat** (the script also opens it for you).

You should see the IRI AI chat page right away. The status can say
**App running · DB later** until SQL is wired up — that is OK for now.

## Step 2 — connect the database (later)

`local.settings.json` already has the Prohance settings. When you are ready:

```text
python diagnose_sql.py
```

Then refresh the chat page. Details can wait until localhost is working.

## URLs

| What | URL |
| --- | --- |
| Chat UI | http://localhost:7179/api/Chat |
| App health | http://localhost:7179/api/Health |
| SQL test | http://localhost:7179/api/TestSqlConnection |

Port **7180**: use `start_iri_chatbot_7180.bat`.
