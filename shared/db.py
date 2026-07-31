import os
import re
from contextlib import contextmanager
from decimal import Decimal
from datetime import datetime

import pymysql
import pymysql.cursors


def _parse_db_url() -> dict:
    url = os.environ.get("DB_URL", "")
    if not url:
        raise RuntimeError("DB_URL environment variable not set")
    url = re.sub(r"^mysql\+pymysql://", "", url)
    m = re.match(r"([^:]+):([^@]*)@([^:/]+):?(\d+)?/(.+)", url)
    if not m:
        raise RuntimeError(f"Cannot parse DB_URL: {url}")
    user, password, host, port, database = m.groups()
    return {
        "host": host,
        "user": user,
        "password": password,
        "database": database,
        "port": int(port) if port else 3306,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "connect_timeout": 10,
    }


@contextmanager
def get_connection():
    conn = pymysql.connect(**_parse_db_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _serialize(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def serialize_row(row: dict) -> dict:
    return {k: _serialize(v) for k, v in row.items()}


def serialize_rows(rows: list) -> list:
    return [serialize_row(r) for r in rows]
