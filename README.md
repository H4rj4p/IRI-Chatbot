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

## Connect to Prohance

1. Run `python app.pyw` and open http://localhost:7179/api/Chat
2. In the **Connect to Prohance** panel, enter the SQL Server address:
   - On the SQL PC itself: click **Try 127.0.0.1**
   - From another PC: on the SQL PC run `ipconfig`, copy the Ethernet/Wi-Fi IPv4
     (usually `192.168.x.x`), paste it, click **Connect**
3. Database `Prohance`, user `VMWinSQLS`, and password are already in `local.settings.json`

Do **not** use `172.18.0.4` from a different PC — that Docker IP only works on the SQL host.

## Settings

Edit `local.settings.json` next to `app.pyw` for SQL Server and OpenAI values.
If it is missing, run:

```text
python repair_settings.py
```
