# IRI AI Chatbot

Python Flask chat UI for SQL Server (`Prohance`) + ChatGPT.

## Run it

```text
pip install -r requirements.txt
python app.pyw
```

Then open **http://localhost:7179/api/Chat**

The browser may open automatically. Leave the terminal open while you use the app.

Status can say **App running · DB later** until SQL is connected — that is fine for now.

## Useful URLs

| What | URL |
| --- | --- |
| Chat UI | http://localhost:7179/api/Chat |
| App health | http://localhost:7179/api/Health |
| SQL test | http://localhost:7179/api/TestSqlConnection |

## Settings

Edit `local.settings.json` next to `app.pyw` for SQL Server and OpenAI values.
If it is missing, run:

```text
python repair_settings.py
```
