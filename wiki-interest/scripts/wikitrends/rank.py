"""Rank language editions (or topics) by a weighted, explainable score.

score = w_growth*norm(clean growth) + w_size*norm(log share_ppm) + w_stability*norm(1/(1+CV))
(CV = variation of the deseasonalised monthly share in the analysis window)
        - penalty for low/medium confidence
norm = min-max across compared items (so scores are relative, not absolute)."""
from __future__ import annotations

import math

from .config import RULES


def parse_weights(s: str | None) -> dict:
    w = dict(RULES["weights"])
    if s:
        for part in s.split(","):
            k, v = part.split("=")
            k = k.strip()
            if k not in w:
                raise ValueError(f"unknown weight '{k}', use growth,size,stability")
            w[k] = float(v)
    total = sum(w.values()) or 1
    return {k: round(v / total, 3) for k, v in w.items()}


def _norm(vals: list[float | None]) -> list[float]:
    xs = [v for v in vals if v is not None]
    if not xs:
        return [0.0] * len(vals)
    lo, hi = min(xs), max(xs)
    return [0.5 if v is None else (1.0 if hi == lo else (v - lo) / (hi - lo)) for v in vals]


def rank(items: list[dict], weights: dict) -> list[dict]:
    """items: {key, growth_clean, share_ppm, k, n, confidence}. Returns sorted list with score & why."""
    if len(items) < 2:
        return []
    g = _norm([i["growth_clean"] for i in items])
    s = _norm([math.log(i["share_ppm"]) if i["share_ppm"] and i["share_ppm"] > 0 else None for i in items])
    st = _norm([i.get("stability") for i in items])
    out = []
    for idx, it in enumerate(items):
        pen = {"low": RULES["rank_pen_low"], "medium": RULES["rank_pen_medium"]}.get(it["confidence"], 0.0)
        parts = {"growth": weights["growth"] * g[idx], "size": weights["size"] * s[idx],
                 "stability": weights["stability"] * st[idx]}
        score = sum(parts.values()) - pen
        out.append({"key": it["key"], "score": round(score, 3), "parts": {k: round(v, 3) for k, v in parts.items()},
                    "penalty": pen})
    out.sort(key=lambda r: -r["score"])
    for n, r in enumerate(out, 1):
        r["rank"] = n
        best = max(r["parts"], key=r["parts"].get)
        worst = min(r["parts"], key=r["parts"].get)
        why = f"strongest factor: {best}"
        if worst != best:
            why += f"; weakest: {worst}"
        if r["penalty"]:
            why += f"; penalised for {'low' if r['penalty'] == RULES['rank_pen_low'] else 'medium'} confidence"
        r["why"] = why
    return out
