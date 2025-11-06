import sqlite3, csv, os
from contextlib import closing
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.getcwd(), "app.sqlite")

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with closing(connect()) as conn, conn:
        # пользователи
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        # заявки
        conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            client_name TEXT,
            client_phone TEXT,
            service TEXT,
            comment TEXT,
            source TEXT
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_service ON leads(service);")

# ---------- Users ----------
def create_user(email: str, name: str, password: str) -> int:
    with closing(connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (email.strip().lower(), name.strip(), generate_password_hash(password), datetime.utcnow().isoformat())
        )
        return cur.lastrowid

def get_user_by_email(email: str):
    with closing(connect()) as conn:
        return conn.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()

def verify_user(email: str, password: str):
    row = get_user_by_email(email)
    if not row: return None
    if check_password_hash(row["password_hash"], password):
        return row
    return None

# ---------- Leads ----------
def add_lead(client_name: str, client_phone: str, service: str, comment: str, source: str = "солнечный луч") -> int:
    with closing(connect()) as conn, conn:
        cur = conn.execute("""
            INSERT INTO leads (created_at, client_name, client_phone, service, comment, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.utcnow().isoformat(), client_name, client_phone, service, comment, source))
        return cur.lastrowid

def _daterange(date_from: str, date_to: str) -> Tuple[str, Tuple[str, str]]:
    start, end = f"{date_from}T00:00:00", f"{date_to}T23:59:59"
    return "created_at BETWEEN ? AND ?", (start, end)

def stats_overview(date_from: str, date_to: str) -> Dict[str, Any]:
    clause, params = _daterange(date_from, date_to)
    with closing(connect()) as conn:
        total = conn.execute(f"SELECT COUNT(*) c FROM leads WHERE {clause}", params).fetchone()["c"]
        by_day = conn.execute(f"""
            SELECT substr(created_at,1,10) day, COUNT(*) c
            FROM leads WHERE {clause} GROUP BY day ORDER BY day
        """, params).fetchall()
        by_service = conn.execute(f"""
            SELECT COALESCE(service,'') service, COUNT(*) c
            FROM leads WHERE {clause} GROUP BY service ORDER BY c DESC
        """, params).fetchall()
        return {
            "total": total,
            "by_day": [(r["day"], r["c"]) for r in by_day],
            "by_service": [(r["service"], r["c"]) for r in by_service],
        }

def export_csv(date_from: str, date_to: str) -> str:
    path = f"leads_{date_from}_{date_to}.csv"
    clause, params = _daterange(date_from, date_to)
    with closing(connect()) as conn, open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id","created_at","client_name","client_phone","service","comment","source"])
        for r in conn.execute(
            f"SELECT id,created_at,client_name,client_phone,service,comment,source FROM leads WHERE {clause} ORDER BY created_at",
            params
        ):
            w.writerow(r)
    return path
