"""SQLite cache.

- Daily pageviews of *closed* months never change -> cached forever.
  `fetched_months` records which (article, month) were fetched, because the
  API omits zero-view days (a missing row is not "unknown").
- The current month is never cached (and never analysed).
- Wikidata/MediaWiki responses -> api_cache with a TTL.
"""
from __future__ import annotations

import sqlite3
import threading
import time

from .config import home

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS pageviews(
  project TEXT, article TEXT, access TEXT, date TEXT, views INTEGER,
  PRIMARY KEY(project, article, access, date));
CREATE TABLE IF NOT EXISTS fetched_months(
  project TEXT, article TEXT, access TEXT, month TEXT, fetched_at REAL,
  PRIMARY KEY(project, article, access, month));
CREATE TABLE IF NOT EXISTS project_monthly(
  project TEXT, access TEXT, month TEXT, views INTEGER,
  PRIMARY KEY(project, access, month));
CREATE TABLE IF NOT EXISTS api_cache(key TEXT PRIMARY KEY, body TEXT, expires_at REAL);
"""


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(home() / "cache.sqlite", check_same_thread=False)
        _conn.executescript(SCHEMA)
    return _conn


def api_get(key: str) -> str | None:
    with _lock:
        row = conn().execute("SELECT body, expires_at FROM api_cache WHERE key=?", (key,)).fetchone()
    if row and row[1] > time.time():
        return row[0]
    return None


def api_put(key: str, body: str, ttl_days: float) -> None:
    with _lock:
        conn().execute("INSERT OR REPLACE INTO api_cache VALUES(?,?,?)", (key, body, time.time() + ttl_days * 86400))
        conn().commit()


def fetched_months(project: str, article: str, access: str) -> set[str]:
    with _lock:
        rows = conn().execute("SELECT month FROM fetched_months WHERE project=? AND article=? AND access=?",
                              (project, article, access)).fetchall()
    return {r[0] for r in rows}


def put_daily(project: str, article: str, access: str, months: list[str], days: dict[str, int]) -> None:
    """Store days of closed months and mark those months as fetched."""
    now = time.time()
    with _lock:
        c = conn()
        c.executemany("INSERT OR REPLACE INTO pageviews VALUES(?,?,?,?,?)",
                      [(project, article, access, d, v) for d, v in days.items() if d[:7] in months])
        c.executemany("INSERT OR REPLACE INTO fetched_months VALUES(?,?,?,?,?)",
                      [(project, article, access, m, now) for m in months])
        c.commit()


def get_daily(project: str, article: str, access: str, start: str, end: str) -> dict[str, int]:
    with _lock:
        rows = conn().execute(
            "SELECT date, views FROM pageviews WHERE project=? AND article=? AND access=? AND date>=? AND date<=?",
            (project, article, access, start, end)).fetchall()
    return dict(rows)


def get_project_monthly(project: str, access: str, months: list[str]) -> dict[str, int]:
    q = "SELECT month, views FROM project_monthly WHERE project=? AND access=? AND month IN (%s)" % ",".join("?" * len(months))
    with _lock:
        return dict(conn().execute(q, (project, access, *months)).fetchall())


def put_project_monthly(project: str, access: str, data: dict[str, int]) -> None:
    with _lock:
        conn().executemany("INSERT OR REPLACE INTO project_monthly VALUES(?,?,?,?)",
                           [(project, access, m, v) for m, v in data.items()])
        conn().commit()


def stats() -> dict:
    with _lock:
        c = conn()
        return {
            "articles_months_cached": c.execute("SELECT COUNT(*) FROM fetched_months").fetchone()[0],
            "api_responses_cached": c.execute("SELECT COUNT(*) FROM api_cache").fetchone()[0],
        }
