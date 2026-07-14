"""Repair local.settings.json with the Prohance SQL + OpenAI settings."""

from __future__ import annotations

import json
import ssl
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = BASE_DIR / "local.settings.json"

OPENAI_KEY = (
    "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"
)
SQL_SERVER = "127.0.0.1,1433"
SQL_SERVER_ALTERNATES = "172.18.0.4,1433;localhost,1433;host.docker.internal,1433;VMWinSQLS,1433"
SQL_DATABASE = "Prohance"
SQL_USER = "VMWinSQLS"
SQL_PASSWORD = "Aks@2026"
APP_URL = "https://raw.githubusercontent.com/H4rj4p/IRI-Chatbot/cursor/sql-server-connection-eb61/app.pyw"
CHAT_URL = "https://raw.githubusercontent.com/H4rj4p/IRI-Chatbot/cursor/sql-server-connection-eb61/chat.html"


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        for encoding in ("utf-8-sig", "utf-16", "utf-8"):
            try:
                return json.loads(SETTINGS_PATH.read_text(encoding=encoding))
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
    existing = str(values.get("SqlPassword") or "").strip()
    if existing in {"", "YOUR_PASSWORD", "PASSWORD"}:
        password = SQL_PASSWORD
    else:
        password = existing

    values["SqlServer"] = SQL_SERVER
    values["SqlServerAlternates"] = SQL_SERVER_ALTERNATES
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
    print(f"SqlDatabase: {SQL_DATABASE}")
    print(f"SqlUser: {SQL_USER}")
    print("SqlPassword: configured")


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
    print("  python diagnose_sql.py")
    print("  python app.pyw")
    print("Then open:")
    print("  http://localhost:7179/api/TestSqlConnection")


if __name__ == "__main__":
    main()
