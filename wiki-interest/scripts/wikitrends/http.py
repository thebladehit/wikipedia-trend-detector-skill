"""HTTP client: User-Agent, retries with backoff, 429 Retry-After, rate limit,
TTL cache for Wikidata/MediaWiki responses and request counters."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import cache
from .config import user_agent


class WitError(Exception):
    """Error that the CLI turns into {"status":"error","code":..,"hint":..}."""

    def __init__(self, code: str, message: str, hint: str = ""):
        super().__init__(message)
        self.code = code
        self.hint = hint


STATS = {"requests_made": 0, "cache_hits": 0}
_lock = threading.Lock()
_last = [0.0]
MIN_INTERVAL = 0.08  # ~12 req/s across threads, well below Wikimedia limits
MAX_RETRIES = 4


def _throttle() -> None:
    with _lock:
        wait = _last[0] + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()


def get_json(url: str, params: dict | None = None, *, allow_404: bool = False, ttl_days: float | None = None):
    """GET JSON. Returns None on 404 when allow_404 (pageviews: "no data").
    ttl_days caches the body in SQLite (used for Wikidata/MediaWiki)."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    if ttl_days:
        hit = cache.api_get(url)
        if hit is not None:
            with _lock:
                STATS["cache_hits"] += 1
            return json.loads(hit)
    body = _download(url, allow_404)
    if body is None:
        return None
    if ttl_days:
        cache.api_put(url, body, ttl_days)
    return json.loads(body)


def _download(url: str, allow_404: bool) -> str | None:
    """Body of the response, retrying 429 (after Retry-After), 5xx and network
    errors with exponential backoff. None for an allowed 404."""
    delay = 1.0
    for attempt in range(MAX_RETRIES + 1):
        last_try = attempt == MAX_RETRIES
        try:
            return _request(url)
        except urllib.error.HTTPError as e:
            if e.code == 404 and allow_404:
                return None
            if e.code == 429:
                retry_after = e.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else delay * 2
                if last_try or wait > 60:
                    raise WitError("rate_limited", f"Wikimedia rate limit (429) for {url}",
                                   "Wait a minute and repeat the same command: data already fetched is cached.")
                time.sleep(wait)
            elif 500 <= e.code < 600 and not last_try:
                time.sleep(delay)
            else:
                raise WitError("http_error", f"HTTP {e.code} for {url}", "Check the title/language code; run `doctor` if it persists.")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if last_try:
                raise WitError("network_error", f"Network error: {e}", "Check internet access; run `doctor`. Cached data is kept.")
            time.sleep(delay)
        delay *= 2
    raise WitError("http_error", f"Failed: {url}", "")


def _request(url: str) -> str:
    _throttle()
    req = urllib.request.Request(url, headers={"User-Agent": user_agent(), "Accept": "application/json"})
    with _lock:
        STATS["requests_made"] += 1
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")
