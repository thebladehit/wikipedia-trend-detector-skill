"""Wikimedia Pageviews REST API with a month-level cache.

Only closed months are requested/cached; only months missing from the cache
are downloaded (one request per article per contiguous gap)."""
from __future__ import annotations

import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from . import cache, months as M
from .http import get_json

BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews"
AGENT = "user"  # humans only; spiders and "automated" traffic excluded by Wikimedia


def project_of(lang: str) -> str:
    return f"{lang}.wikipedia"


def _enc(title: str) -> str:
    return urllib.parse.quote(title.replace(" ", "_"), safe="")


def _gaps(missing: list[str]) -> list[tuple[str, str]]:
    """Group sorted months into contiguous ranges."""
    out = []
    for m in sorted(missing):
        if out and M.add(out[-1][1], 1) == m:
            out[-1] = (out[-1][0], m)
        else:
            out.append((m, m))
    return out


def article_daily(lang: str, title: str, months: list[str], access: str = "all-access") -> dict[str, int]:
    """Daily views for closed `months`. Missing days (omitted by API) = 0."""
    project = project_of(lang)
    have = cache.fetched_months(project, title, access)
    missing = [m for m in months if m not in have]
    for first, last in _gaps(missing):
        url = (f"{BASE}/per-article/{project}/{access}/{AGENT}/{_enc(title)}/daily/"
               f"{first.replace('-', '')}0100/{last.replace('-', '')}{M.days_in(last):02d}00")
        data = get_json(url, allow_404=True)
        days = {}
        for it in (data or {}).get("items", []):
            ts = it["timestamp"]
            days[f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"] = int(it["views"])
        cache.put_daily(project, title, access, M.span(first, last), days)
    got = cache.get_daily(project, title, access, f"{months[0]}-01", f"{months[-1]}-31")
    return {d: got.get(d, 0) for m in months for d in M.day_list(m)}


def project_monthly(lang: str, months: list[str], access: str = "all-access") -> dict[str, int]:
    """Total human views of the language edition — the normalisation base."""
    project = project_of(lang)
    have = cache.get_project_monthly(project, access, months)
    missing = [m for m in months if m not in have]
    if missing:
        first, last = missing[0], missing[-1]
        url = (f"{BASE}/aggregate/{project}/{access}/{AGENT}/monthly/"
               f"{first.replace('-', '')}0100/{last.replace('-', '')}{M.days_in(last):02d}00")
        data = get_json(url, allow_404=True)
        new = {}
        for it in (data or {}).get("items", []):
            ts = it["timestamp"]
            new[f"{ts[:4]}-{ts[4:6]}"] = int(it["views"])
        cache.put_project_monthly(project, access, new)
        have.update(new)
    return {m: have.get(m, 0) for m in months}


def project_countries(lang: str, month: str) -> list[dict]:
    """Top countries reading a language edition (bucketed, privacy-limited)."""
    y, m = month.split("-")
    url = f"{BASE}/top-by-country/{project_of(lang)}/all-access/{y}/{m}"
    data = get_json(url, allow_404=True, ttl_days=365)
    if not data:
        return []
    rows = data["items"][0]["countries"]
    total = sum(r["views_ceil"] for r in rows) or 1
    return [{"country": r["country"], "rank": r["rank"], "share": r["views_ceil"] / total} for r in rows]


def fetch_many(jobs: list[tuple], workers: int = 6) -> list:
    """Run (fn, *args) jobs in parallel; shared rate limiter lives in http.py."""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(fn, *args) for fn, *args in jobs]
        return [f.result() for f in futs]
