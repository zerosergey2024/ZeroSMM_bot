# sheets_reader.py
import os
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv, find_dotenv
import gspread
from google.oauth2.service_account import Credentials

# ----------------------------
# ENV
# ----------------------------
load_dotenv(find_dotenv() or ".env")

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_JSON = os.getenv("GOOGLE_SERVICE_JSON", "credentials.json")

if not GOOGLE_SHEET_ID:
    raise RuntimeError("GOOGLE_SHEET_ID не задан в .env")

_creds = Credentials.from_service_account_file(SERVICE_JSON, scopes=SCOPES)
_gc    = gspread.authorize(_creds)

# Унифицированные ключи, которые будем возвращать наружу
CANON_KEYS = ["created_at", "client_name", "client_phone", "service", "comment", "source", "manager", "city", "lead_status", "price"]

# Возможные варианты заголовков -> к каноническим ключам
HEADER_NORMALIZE = {
    # дата/время
    "дата и время": "created_at",
    "дата": "created_at",
    "created_at": "created_at",

    # имя
    "имя": "client_name",
    "клиент": "client_name",
    "client_name": "client_name",

    # телефон
    "телефон": "client_phone",
    "номер": "client_phone",
    "client_phone": "client_phone",
    "phone": "client_phone",

    # услуга
    "вид услуги": "service",
    "услуга": "service",
    "service": "service",

    # комментарий
    "комментарий": "comment",
    "comment": "comment",

    # источник
    "источник": "source",
    "source": "source",

    # доп. поля (заглушки)
    "менеджер": "manager",
    "manager": "manager",
    "город": "city",
    "city": "city",
    "статус": "lead_status",
    "lead_status": "lead_status",
    "цена": "price",
    "стоимость": "price",
    "price": "price",
}

def _open_ws():
    sh = _gc.open_by_key(GOOGLE_SHEET_ID)
    return sh.sheet1  # первая вкладка

def _parse_iso_date(s: str) -> Optional[date]:
    """Поддержка ISO 8601 с TZ (2025-11-06T10:38:05+03:00) и простых дат."""
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    fmts = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]
    for f in fmts:
        try:
            dt = datetime.strptime(s[:len(f)], f)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
            return dt.date()
        except Exception:
            continue
    return None

def _normalize_header_row(header: List[str]) -> Dict[str, int]:
    """
    Приводим произвольные названия столбцов (RU/EN) к каноническим ключам.
    Возвращаем словарь: { 'created_at': idx, 'client_name': idx, ... }
    """
    idx_map: Dict[str, int] = {}
    for i, h in enumerate(header):
        key = (h or "").strip().lower()
        canon = HEADER_NORMALIZE.get(key)
        if canon and canon not in idx_map:
            idx_map[canon] = i
    return idx_map

def read_leads(date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Читает строки из таблицы и приводит к ключам:
    created_at, client_name, client_phone, service, comment, source, manager, city, lead_status, price

    date_from/date_to — строки "YYYY-MM-DD" (опционально).
    """
    ws = _open_ws()
    values = ws.get_all_values()
    if not values:
        return []

    header = [ (h or "").strip() for h in values[0] ]
    idx_map = _normalize_header_row(header)
    rows = values[1:]

    # даты фильтра
    d_from = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
    d_to   = datetime.strptime(date_to,   "%Y-%m-%d").date() if date_to   else None

    def at(r: List[str], i: Optional[int]) -> str:
        if i is None or i < 0:
            return ""
        return (r[i] if 0 <= i < len(r) else "").strip()

    out: List[Dict[str, Any]] = []
    for r in rows:
        row: Dict[str, Any] = {}
        # заполняем канонические поля
        for k in CANON_KEYS:
            col_idx = idx_map.get(k, None)
            row[k] = at(r, col_idx)

        # фильтрация по дате, если задана
        if d_from or d_to:
            d = _parse_iso_date(row.get("created_at", ""))
            if not d:
                continue
            if d_from and d < d_from:
                continue
            if d_to and d > d_to:
                continue

        out.append(row)

    return out

def compute_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Возвращает:
      total        — всего
      by_day       — [(YYYY-MM-DD, count), ...]
      by_service   — [(service, count), ...] (сортировка по убыванию)
    """
    total = len(rows)
    by_day: Dict[str, int] = {}
    by_service: Dict[str, int] = {}

    for r in rows:
        # по дням
        d = _parse_iso_date(r.get("created_at", ""))
        key_day = d.isoformat() if d else "(без даты)"
        by_day[key_day] = by_day.get(key_day, 0) + 1

        # по услугам
        s = (r.get("service") or "").strip() or "(не указано)"
        by_service[s] = by_service.get(s, 0) + 1

    by_day_sorted = sorted(by_day.items(), key=lambda x: x[0])
    by_srv_sorted = sorted(by_service.items(), key=lambda x: (-x[1], x[0]))

    return {"total": total, "by_day": by_day_sorted, "by_service": by_srv_sorted}

# Локальный тест: python sheets_reader.py --from 2025-11-01 --to 2025-11-06
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="dfrom")
    parser.add_argument("--to",   dest="dto")
    args = parser.parse_args()

    leads = read_leads(args.dfrom, args.dto)
    print(f"rows: {len(leads)}")
    if leads[:1]:
        print("sample row:", leads[0])
    stats = compute_summary(leads)
    print(stats)

