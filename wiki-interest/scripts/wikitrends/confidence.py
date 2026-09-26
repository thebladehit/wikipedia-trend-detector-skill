"""Confidence score: start at 10, apply penalties and caps. Each rule adds a
human-readable reason (uk/en). Caps are shown explicitly
("medium (8/10, capped: small volume …)") so a small model does not mix up
score and level."""
from __future__ import annotations

from .config import RULES

LEVELS = ["low", "medium", "high"]

REASONS = {
    "vol_low": {"en": "very little data: median {v} views/month (< {t})", "uk": "дуже мало даних: медіана {v} переглядів/міс (< {t})"},
    "vol_medium": {"en": "small volume: median {v} views/month (< {t})", "uk": "невеликий обсяг: медіана {v} переглядів/міс (< {t})"},
    "history": {"en": "only {h} months of history (< {t})", "uk": "лише {h} міс. історії (< {t})"},
    "proxy": {"en": "a proxy article measures a related but different concept", "uk": "стаття-замінник вимірює близьке, але інше поняття"},
    "not_consistent": {"en": "not consistent: {k} of {n} months above the same month a year earlier",
                       "uk": "непослідовно: лише {k} з {n} місяців вищі, ніж рік тому"},
    "no_yoy": {"en": "not enough history for a year-over-year comparison", "uk": "недостатньо історії для порівняння рік до року"},
    "spikes": {"en": "{s} of the raw increase came from short spikes", "uk": "{s} сирого приросту дали короткі спайки"},
    "divergence": {"en": "the basket total grows but the median article does not — growth comes from one or two pages",
                   "uk": "сума кошика росте, а медіанна стаття — ні: ріст дають одна-дві сторінки"},
    "breadth": {"en": "only {b} of basket articles move in the same direction as the topic",
                "uk": "лише {b} статей кошика рухаються в тому ж напрямі, що й тема"},
    "bot": {"en": "possible automated traffic (unusual desktop share)", "uk": "можливий автоматизований трафік (нетипова частка desktop)"},
    "late": {"en": "some articles appeared during the period", "uk": "частина статей з'явилась посеред періоду"},
    "ok": {"en": "large volume, consistent month to month, not driven by spikes",
           "uk": "великий обсяг, послідовно місяць до місяця, не через спайки"},
}
CAPPED = {"en": "capped", "uk": "обмежено"}
LEVEL_NAMES = {"en": {"low": "low", "medium": "medium", "high": "high"},
               "uk": {"low": "низька", "medium": "середня", "high": "висока"}}


def _level(score: int) -> str:
    if score >= RULES["conf_high_min"]:
        return "high"
    if score >= RULES["conf_medium_min"]:
        return "medium"
    return "low"


def assess(m: dict) -> dict:
    """m: metrics of one language (see analyze.py). Returns codes; render() makes text.

    The level comes from the score, but can never exceed the lowest cap."""
    cap, caps = _caps(m)
    score, reasons = _penalties(m)
    level = _level(score)
    if LEVELS.index(cap) < LEVELS.index(level):
        level = cap  # capped: the caps explain the level
    else:
        reasons, caps = reasons + caps, []  # not binding: caps are just more reasons
    if not reasons and not caps:
        reasons.append(("ok", {}))
    return {"level": level, "score": score, "_caps": caps, "_reasons": reasons}


def _caps(m: dict) -> tuple[str, list[tuple[str, dict]]]:
    """Upper limits of the level: too little data, short history, proxy article.
    Returns (lowest cap, [(reason code, params)])."""
    caps: list[tuple[str, str, dict]] = []
    vol = m["median_monthly_views"]
    if vol < RULES["vol_low_cap"]:
        caps.append(("low", "vol_low", {"v": f"{vol:.0f}", "t": RULES["vol_low_cap"]}))
    elif vol < RULES["vol_medium_cap"]:
        caps.append(("medium", "vol_medium", {"v": f"{vol:.0f}", "t": RULES["vol_medium_cap"]}))
    if m["history_months"] < RULES["history_min_months"]:
        caps.append(("low", "history", {"h": m["history_months"], "t": RULES["history_min_months"]}))
    if m.get("proxy"):
        caps.append(("medium", "proxy", {}))
    lowest = min((level for level, _, _ in caps), key=LEVELS.index, default="high")
    return lowest, [(code, kw) for _, code, kw in caps]


def _penalties(m: dict) -> tuple[int, list[tuple[str, dict]]]:
    """Start at conf_start and subtract a penalty per problem. Returns (score, reasons)."""
    score = RULES["conf_start"]
    reasons: list[tuple[str, dict]] = []

    def penalise(rule: str, code: str, **kw):
        nonlocal score
        score -= RULES[rule]
        reasons.append((code, kw))

    if m["p"] is None or m["p"] >= RULES["binom_alpha"]:
        if m.get("k") is not None:
            penalise("pen_not_significant", "not_consistent", k=m["k"], n=m["n"])
        else:
            penalise("pen_not_significant", "no_yoy")
    if m["spike_share"] > RULES["spike_driven_share"]:
        penalise("pen_spike_driven", "spikes", s=f"{m['spike_share']:.0%}")
    if m.get("divergence"):
        penalise("pen_divergence", "divergence")
    if m.get("agreement") is not None and m["n_articles"] > 2 and m["agreement"] < RULES["low_breadth"]:
        penalise("pen_low_breadth", "breadth", b=f"{m['agreement']:.0%}")
    if m.get("bot_suspect"):
        penalise("pen_bot", "bot")
    if m.get("late_start"):
        penalise("pen_late_start", "late")
    return max(0, score), reasons


def render(c: dict, out: str) -> dict:
    """Add human text in language `out`: label, reasons, capped_by."""
    fmt = lambda items: [REASONS[code][out].format(**kw) for code, kw in items]  # noqa: E731
    caps = fmt(c["_caps"])
    label = f"{LEVEL_NAMES[out][c['level']]} ({c['score']}/10" + (f", {CAPPED[out]}: " + "; ".join(caps) if caps else "") + ")"
    return {"level": c["level"], "score": c["score"], "label": label, "capped_by": caps, "reasons": fmt(c["_reasons"])}
