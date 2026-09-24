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
    delay = 1.0
    for attempt in range(MAX_RETRIES + 1):
        _throttle()
        req = urllib.request.Request(url, headers={"User-Agent": user_agent(), "Accept": "application/json"})
        with _lock:
            STATS["requests_made"] += 1
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode("utf-8")
            if ttl_days:
                cache.api_put(url, body, ttl_days)
            return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 404 and allow_404:
                return None
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                wait = float(ra) if ra and ra.isdigit() else delay * 2
                if attempt < MAX_RETRIES and wait <= 60:
                    time.sleep(wait)
                    delay *= 2
                    continue
                raise WitError("rate_limited", f"Wikimedia rate limit (429) for {url}",
                               "Wait a minute and repeat the same command: data already fetched is cached.")
            if 500 <= e.code < 600 and attempt < MAX_RETRIES:
                time.sleep(delay)
                delay *= 2
                continue
            raise WitError("http_error", f"HTTP {e.code} for {url}", "Check the title/language code; run `doctor` if it persists.")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < MAX_RETRIES:
                time.sleep(delay)
                delay *= 2
                continue
            raise WitError("network_error", f"Network error: {e}", "Check internet access; run `doctor`. Cached data is kept.")
    raise WitError("http_error", f"Failed: {url}", "")
