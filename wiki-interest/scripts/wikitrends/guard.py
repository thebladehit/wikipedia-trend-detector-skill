"""Hallucination guard for the agent's summary before it goes into a PDF.

Blocking:  numbers not present in the analysis; claims about willingness to
           pay / market demand.
Warning:   a sentence that mentions a language contradicts its verdict;
           "market"/"country" wording instead of "language edition".
Direction checks only warn: keyword matching in free text is brittle and must
not trap a small model in a reject loop."""
from __future__ import annotations

import json
import re


NUM = re.compile(r"(?<![\w.])[-+−–]?\d+(?:[.,]\d+)?(?:\s?%)?")

BLOCK = [
    (r"готов\w*\s+(?:\w+\s+)?плат", "claims willingness to pay — pageviews do not show that"),
    (r"willing(?:ness)?\s+to\s+pay", "claims willingness to pay — pageviews do not show that"),
    (r"\bwill\s+(?:buy|pay)\b", "claims purchase intent — pageviews do not show that"),
    (r"попит\s+на\s+ринку|market\s+demand", "claims market demand — pageviews measure interest in a language edition"),
]
NEGATION = re.compile(r"\b(?:не|ні|not|no|doesn't|does not|don't)\b|≠", re.I)
WARN_WORDS = [(r"\bринк\w*|\bmarket\w*", "say 'language edition' (мовний розділ), not 'market'"),
              (r"\bкраїн\w*|\bcountr\w*", "a language edition is not a country — check the wording")]

UP = r"(зроста|росте|зріс|збільш|рост|grow|rising|rise|increas|up\b)"
DOWN = r"(пада|знижу|зменш|спад|declin|fall|drop|decreas)"
FLAT = r"(стабільн|без змін|пласк|flat|stable|unchanged)"


def _nums(text: str) -> list[tuple[str, float, bool]]:
    out = []
    for m in NUM.finditer(text):
        s = m.group(0)
        pct = s.endswith("%")
        v = s.replace("%", "").replace("−", "-").replace("–", "-").replace(",", ".").strip()
        try:
            out.append((s.strip(), float(v), pct))
        except ValueError:
            pass
    return out


def allowed_numbers(compact: dict) -> set[float]:
    """Every number that appears anywhere in the compact result (verdicts,
    table, ranking, basket, assumptions…) plus harmless small integers."""
    text = json.dumps({k: v for k, v in compact.items() if k not in ("files", "next_steps", "api")}, ensure_ascii=False)
    vals = {abs(v) for _, v, _ in _nums(text)}
    vals |= set(range(0, 13)) | {24, 36, 100}
    return vals


def _ok(v: float, allowed: set[float], pct: bool) -> bool:
    v = abs(v)
    tol = 1.0 if pct else max(0.5, 0.02 * v)
    return any(abs(v - a) <= tol for a in allowed)


def check(summary: str, compact: dict) -> dict:
    problems, warns = [], []
    allowed = allowed_numbers(compact)
    for s, v, pct in _nums(summary):
        if 1990 <= v <= 2100 and not pct:
            continue  # years
        if not _ok(v, allowed, pct):
            problems.append(f"number {s} is not in the analysis — use only numbers from verdicts/table")
    sentences = re.split(r"(?<=[.!?;])\s+|\n", summary)
    for sent in sentences:
        low = sent.casefold()
        for pat, why in BLOCK:
            m = re.search(pat, low)
            if m and not NEGATION.search(low[max(0, m.start() - 25):m.start()]):
                problems.append(f"'{m.group(0)}': {why}")
        for pat, why in WARN_WORDS:
            if re.search(pat, low):
                warns.append(why)
        results = compact.get("_directions", {})
        for lang, direction in results.items():
            if not re.search(rf"(?<![a-z]){lang}(?![a-z])", low):
                continue
            says_up, says_down, says_flat = (bool(re.search(p, low)) for p in (UP, DOWN, FLAT))
            if direction in ("flat", "declining", "unclear") and says_up and not says_down and not NEGATION.search(low):
                warns.append(f"'{sent.strip()[:80]}' sounds like growth, but {lang} verdict is {direction}")
            if direction in ("rising", "flat", "unclear") and says_down and not says_up and not NEGATION.search(low):
                warns.append(f"'{sent.strip()[:80]}' sounds like decline, but {lang} verdict is {direction}")
            if direction == "rising" and says_flat and not says_up:
                warns.append(f"'{sent.strip()[:80]}' sounds flat, but {lang} verdict is rising")
    status = "rejected" if problems else "ok"
    res = {"status": status, "problems": problems, "warnings": sorted(set(warns))}
    if problems:
        res["allowed_numbers_hint"] = _key_numbers(compact)
    return res


def _key_numbers(compact: dict) -> dict:
    return {"verdicts": compact.get("verdicts"), "table_md": compact.get("table_md")}
