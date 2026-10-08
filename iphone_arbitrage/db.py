import sqlite3
from datetime import datetime, timezone

from .models import Item, PricePoint

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL,
    item_key TEXT NOT NULL,
    model TEXT NOT NULL,
    capacity TEXT NOT NULL,
    color TEXT NOT NULL,
    price INTEGER NOT NULL,
    in_stock INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prices_lookup ON prices (source, item_key, fetched_at);
CREATE TABLE IF NOT EXISTS alerts (
    item_key TEXT PRIMARY KEY,
    last_profit INTEGER NOT NULL,
    sent_at TEXT NOT NULL
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def save_prices(conn: sqlite3.Connection, points: list[PricePoint]) -> None:
    now = _now()
    conn.executemany(
        "INSERT INTO prices (fetched_at, source, item_key, model, capacity, color, price, in_stock)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (now, p.source, p.item.key, p.item.model, p.item.capacity, p.item.color,
             p.price, int(p.in_stock))
            for p in points
        ],
    )
    conn.commit()


def latest_price(conn: sqlite3.Connection, source: str, item: Item) -> PricePoint | None:
    row = conn.execute(
        "SELECT price, in_stock FROM prices WHERE source=? AND item_key=?"
        " ORDER BY fetched_at DESC, id DESC LIMIT 1",
        (source, item.key),
    ).fetchone()
    return PricePoint(source, item, row[0], bool(row[1])) if row else None


def last_alert_profit(conn: sqlite3.Connection, item: Item) -> int | None:
    row = conn.execute("SELECT last_profit FROM alerts WHERE item_key=?", (item.key,)).fetchone()
    return row[0] if row else None


def record_alert(conn: sqlite3.Connection, item: Item, profit: int) -> None:
    conn.execute(
        "INSERT INTO alerts (item_key, last_profit, sent_at) VALUES (?, ?, ?)"
        " ON CONFLICT(item_key) DO UPDATE SET last_profit=excluded.last_profit, sent_at=excluded.sent_at",
        (item.key, profit, _now()),
    )
    conn.commit()


def clear_alert(conn: sqlite3.Connection, item: Item) -> None:
    conn.execute("DELETE FROM alerts WHERE item_key=?", (item.key,))
    conn.commit()
