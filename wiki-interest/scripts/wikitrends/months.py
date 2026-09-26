"""Month arithmetic on 'YYYY-MM' strings."""
from __future__ import annotations

import calendar
import datetime as dt

from .config import PAGEVIEWS_START


def add(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    idx = y * 12 + (m - 1) + n
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def span(first: str, last: str) -> list[str]:
    out, m = [], first
    while m <= last:
        out.append(m)
        m = add(m, 1)
    return out


def last_complete(today: dt.date | None = None) -> str:
    """Last fully finished month. The current month is never analysed."""
    today = today or dt.date.today()
    return add(f"{today.year:04d}-{today.month:02d}", -1)


def days_in(month: str) -> int:
    y, m = map(int, month.split("-"))
    return calendar.monthrange(y, m)[1]


def day_list(month: str) -> list[str]:
    return [f"{month}-{d:02d}" for d in range(1, days_in(month) + 1)]


def window(months: int, end: str | None = None, extra: int = 12) -> tuple[list[str], list[str], list[str]]:
    """Return (fetch_months, analysis_months, assumptions).

    Fetch `extra` months more than requested: YoY for the first analysed year
    needs the year before it. Everything is clipped at 2015-07."""
    notes = []
    end = end or last_complete()
    a_first = add(end, -(months - 1))
    f_first = add(a_first, -extra)
    if a_first < PAGEVIEWS_START:
        notes.append(("clip", {"s": PAGEVIEWS_START}))
        a_first = PAGEVIEWS_START
    if f_first < PAGEVIEWS_START:
        f_first = PAGEVIEWS_START
    return span(f_first, end), span(a_first, end), notes
