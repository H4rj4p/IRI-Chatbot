"""Repair local.settings.json and refresh app.pyw from the chatbot branch."""

from __future__ import annotations

import json
import ssl
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = BASE_DIR / "local.settings.json"
EXAMPLE_PATH = BASE_DIR / "local.settings.example.json"

OPENAI_KEY = (
    "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"
)
SQL_SERVER = "172.18.0.4,1433"
SQL_DATABASE = "Prohance"
SQL_USER = "VMWinSQLS"
APP_URL = "https://raw.githubusercontent.com/H4rj4p/IRI-Chatbot/cursor/chatbot-1828/app.pyw"
CHAT_URL = "https://raw.githubusercontent.com/H4rj4p/IRI-Chatbot/cursor/chatbot-1828/chat.html"


def load_settings() -> dict:
    for path in (SETTINGS_PATH, EXAMPLE_PATH):
        if not path.exists():
            continue
        for encoding in ("utf-8-sig", "utf-16", "utf-8"):
            try:
                return json.loads(path.read_text(encoding=encoding))
            except Exception:
                continue
    return {"IsEncrypted": False, "Values": {}}


def build_connection_string(password: str) -> str:
    return (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={SQL_SERVER};"
        f"Database={SQL_DATABASE};"
        f"User ID={SQL_USER};"
        f"Password={password};"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )


def repair_settings() -> None:
    settings = load_settings()
    values = settings.setdefault("Values", {})
    password = str(values.get("SqlPassword") or "YOUR_PASSWORD").strip() or "YOUR_PASSWORD"

    values["SqlServer"] = SQL_SERVER
    values["SqlDatabase"] = SQL_DATABASE
    values["SqlUser"] = SQL_USER
    values["SqlPassword"] = password
    values["SqlConnectionString"] = build_connection_string(password)
    values["OpenAIApiKey"] = OPENAI_KEY
    values["OpenAIModel"] = values.get("OpenAIModel") or "gpt-4o-mini"

    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    print(f"Updated: {SETTINGS_PATH}")
    print(f"OpenAIApiKey now starts with: {OPENAI_KEY[:8]}...")
    print(f"SqlServer: {SQL_SERVER}")
    if password in {"", "YOUR_PASSWORD", "PASSWORD"}:
        print("SqlPassword is still YOUR_PASSWORD — replace it with your real SQL password.")
    else:
        print("SqlPassword: kept your existing password value.")


def download(url: str, target: Path) -> None:
    context = ssl.create_default_context()
    with urllib.request.urlopen(url, context=context, timeout=60) as response:
        data = response.read()
    target.write_bytes(data)
    print(f"Downloaded: {target.name} ({len(data)} bytes)")


def main() -> None:
    print(f"Repairing folder: {BASE_DIR}")
    repair_settings()
    try:
        download(APP_URL, BASE_DIR / "app.pyw")
        download(CHAT_URL, BASE_DIR / "chat.html")
    except Exception as exc:
        print(f"Could not download latest app files: {exc}")
        print("Settings were still updated. Continue with your current app.pyw.")
    print()
    print("Done. Now run:")
    print("  python app.pyw")
    print("Then open:")
    print("  http://localhost:7179/api/TestSqlConnection")


if __name__ == "__main__":
    main()
