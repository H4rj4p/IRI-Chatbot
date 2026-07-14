"""Diagnose SQL Server connectivity for the IRI chatbot.

Run on the same Windows PC that should talk to SQL Server:

    python diagnose_sql.py
"""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = BASE_DIR / "local.settings.json"


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        print("No local.settings.json found. Run: python repair_settings.py")
        return {}
    for encoding in ("utf-8-sig", "utf-16", "utf-8"):
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding=encoding))
        except Exception as exc:
            print(f"Could not parse {SETTINGS_PATH.name}: {exc}")
            return {}
    return {}


def split_host_port(server: str) -> tuple[str, int]:
    text = (server or "").strip()
    if not text:
        return "", 1433
    if "," in text:
        host, port = text.split(",", 1)
        try:
            return host.strip(), int(port.strip() or "1433")
        except ValueError:
            return host.strip(), 1433
    return text, 1433


def is_docker_ip(host: str) -> bool:
    return host.startswith(("172.16.", "172.17.", "172.18.", "172.19.", "172.2", "172.3"))


def tcp_check(host: str, port: int, timeout: float = 3.0) -> str:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "OPEN"
    except socket.timeout:
        return "TIMEOUT"
    except OSError as exc:
        return f"CLOSED/ERROR ({exc})"


def build_odbc(server: str, database: str, user: str, password: str) -> str:
    # Brace-escape passwords that contain ODBC special characters such as @.
    if any(char in password for char in "{}[];,=!@"):
        password = "{" + password.replace("}", "}}") + "}"
    return (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={server};"
        f"Database={database};"
        f"User ID={user};"
        f"Password={password};"
        "Encrypt=yes;TrustServerCertificate=yes;LoginTimeout=5;"
    )


def main() -> int:
    print(f"Folder: {BASE_DIR}")
    print(f"Settings file: {SETTINGS_PATH if SETTINGS_PATH.exists() else '(missing)'}")
    print()

    try:
        import pyodbc
    except Exception as exc:
        print(f"FAIL: pyodbc not installed ({exc})")
        print("Fix: pip install -r requirements.txt")
        return 1

    drivers = list(pyodbc.drivers())
    print("ODBC drivers:", ", ".join(drivers) if drivers else "(none)")
    if not any("SQL Server" in driver for driver in drivers):
        print("FAIL: Install Microsoft ODBC Driver 18 for SQL Server.")
        return 1
    print("OK: SQL Server ODBC driver present")
    print()

    settings = load_settings()
    values = settings.get("Values", settings) if isinstance(settings, dict) else {}
    server = str(values.get("SqlServer") or values.get("SqlServerHost") or "").strip()
    database = str(values.get("SqlDatabase") or "").strip()
    user = str(values.get("SqlUser") or "").strip()
    password = str(values.get("SqlPassword") or "").strip()

    if not server and values.get("SqlConnectionString"):
        parts = {}
        for part in str(values["SqlConnectionString"]).split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                parts[key.strip().lower()] = value.strip()
        server = parts.get("server", "")
        database = database or parts.get("database", "")
        user = user or parts.get("user id", "") or parts.get("uid", "")
        password = password or parts.get("password", "") or parts.get("pwd", "")

    print(f"Configured SqlServer: {server or '(missing)'}")
    print(f"Configured database:  {database or '(missing)'}")
    print(f"Configured user:      {user or '(missing)'}")
    print(f"Password set:         {bool(password) and password not in {'YOUR_PASSWORD', 'PASSWORD'}}")
    print()

    if not server or not database or not user or not password:
        print("FAIL: Fill SqlServer, SqlDatabase, SqlUser, SqlPassword in local.settings.json")
        print("Tip: run python repair_settings.py")
        return 1

    host, port = split_host_port(server)
    candidates = [server]
    # Always try local + Docker-published options so the same settings work
    # when this script runs on the SQL Server PC.
    for alt in (
        f"127.0.0.1,{port}",
        f"localhost,{port}",
        f"host.docker.internal,{port}",
        f"172.18.0.4,{port}",
        f"VMWinSQLS,{port}",
    ):
        if alt not in candidates:
            candidates.append(alt)
    extras = str(values.get("SqlServerAlternates") or "").strip()
    if extras:
        # Support "host,port;host2,port2" and legacy comma-paired lists.
        chunks = [c.strip() for c in extras.replace("\n", ";").split(";") if c.strip()]
        if len(chunks) == 1 and chunks[0].count(",") > 1:
            pieces = [p.strip() for p in chunks[0].split(",") if p.strip()]
            index = 0
            while index < len(pieces):
                host_part = pieces[index]
                if index + 1 < len(pieces) and pieces[index + 1].isdigit():
                    part = f"{host_part},{pieces[index + 1]}"
                    index += 2
                else:
                    part = host_part
                    index += 1
                if part and part not in candidates:
                    candidates.append(part)
        else:
            for part in chunks:
                if part and part not in candidates:
                    candidates.append(part)
    if is_docker_ip(host):
        print(
            f"NOTE: {host} looks like a Docker/internal IP. "
            "On the SQL Server PC, 127.0.0.1 is tried automatically."
        )
        print()

    for candidate in candidates:
        cand_host, cand_port = split_host_port(candidate)
        tcp = tcp_check(cand_host, cand_port)
        print(f"TCP {cand_host}:{cand_port} -> {tcp}")
        if tcp != "OPEN":
            continue
        cs = build_odbc(candidate, database, user, password)
        try:
            with pyodbc.connect(cs, timeout=5, autocommit=True) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT DB_NAME() AS db, @@VERSION AS ver")
                    row = cursor.fetchone()
            print(f"SUCCESS: connected to {candidate}")
            print(f"  Database: {row[0]}")
            print(f"  Version:  {str(row[1]).splitlines()[0]}")
            if candidate != server:
                print()
                print(f"Update local.settings.json SqlServer to \"{candidate}\" and save.")
            print()
            print("Next: python app.pyw")
            print("Then open http://localhost:7179/api/TestSqlConnection")
            return 0
        except Exception as exc:
            print(f"ODBC login to {candidate} failed: {exc}")

    print()
    print("FAIL: Could not complete a SQL Server login.")
    print("Do this on the SQL Server machine:")
    print("  1. Confirm SQL Server is running and TCP 1433 is enabled.")
    print("  2. If SQL is in Docker published to the host, set SqlServer to 127.0.0.1,1433")
    print("  3. From another PC, use the Ethernet/Wi-Fi IPv4 from ipconfig (not 172.18.x.x)")
    print("  4. Allow firewall TCP 1433 and SQL authentication for user", user)
    return 2


if __name__ == "__main__":
    sys.exit(main())
