"""Synthetic daily series with a known answer."""
import numpy as np

from wikitrends import months as M

FETCH = M.span("2023-09", "2026-08")      # 36 months
ANALYSIS = M.span("2024-09", "2026-08")   # 24 months


def daily(level_fn, months=FETCH, seed=0, spikes=None):
    """level_fn(month_index, month_str) -> expected daily views. Poisson noise.
    spikes: {date: extra_views}"""
    rng = np.random.default_rng(seed)
    out = {}
    for i, m in enumerate(months):
        for d in M.day_list(m):
            out[d] = int(rng.poisson(max(level_fn(i, m), 0)))
    for d, v in (spikes or {}).items():
        out[d] = out.get(d, 0) + v
    return out


def project(level=1_000_000, months=FETCH):
    return {m: level * M.days_in(m) for m in months}


def article(title, daily_views, main=False, qid=None):
    return {"qid": qid or f"Q{abs(hash(title)) % 10000}", "label": title, "title": title, "daily": daily_views, "main": main}
