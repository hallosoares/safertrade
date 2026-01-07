import json
import os
import sqlite3
import time
from pathlib import Path

# Import ROOT_DIR from shared.paths for proper path resolution
from shared.paths import ROOT_DIR

ROOT = ROOT_DIR
SQLITE_PATH = os.getenv("SQLITE_PATH", str(ROOT / "shared" / "safertrade.sqlite"))
SCHEMA = ROOT / "shared" / "sql" / "schema.sql"


def connect():
    Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH, isolation_level=None, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def apply_schema(conn=None):
    close = False
    if conn is None:
        conn, close = connect(), True
    with open(SCHEMA, encoding="utf-8") as f:
        conn.executescript(f.read())
    if close:
        conn.close()


def upsert_validation(
    item_key: str,
    passed: bool,
    edge_bps: float,
    notional_usd: float,
    gas_gwei: float,
    details: dict,
):
    conn = connect()
    conn.execute(
        "INSERT INTO validations(item_key, passed, edge_bps, notional_usd, gas_gwei, details_json, created_at) VALUES(?,?,?,?,?,?,?)",
        (
            item_key,
            1 if passed else 0,
            edge_bps,
            notional_usd,
            gas_gwei,
            json.dumps(details)[:20000],
            int(time.time()),
        ),
    )
    conn.close()
