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
    """m: metrics of one language (see analyze.py). Returns codes; render() makes text."""
    score = RULES["conf_start"]
    cap = "high"
    reasons: list[tuple[str, dict]] = []
    caps: list[tuple[str, dict]] = []

    def set_cap(level: str, code: str, **kw):
        nonlocal cap
        if LEVELS.index(level) < LEVELS.index(cap):
            cap = level
        caps.append((code, kw))

    vol = m["median_monthly_views"]
    if vol < RULES["vol_low_cap"]:
        set_cap("low", "vol_low", v=f"{vol:.0f}", t=RULES["vol_low_cap"])
    elif vol < RULES["vol_medium_cap"]:
        set_cap("medium", "vol_medium", v=f"{vol:.0f}", t=RULES["vol_medium_cap"])
    if m["history_months"] < RULES["history_min_months"]:
        set_cap("low", "history", h=m["history_months"], t=RULES["history_min_months"])
    if m.get("proxy"):
        set_cap("medium", "proxy")

    if m["p"] is None or m["p"] >= RULES["binom_alpha"]:
        score -= RULES["pen_not_significant"]
        reasons.append(("not_consistent", {"k": m["k"], "n": m["n"]}) if m.get("k") is not None else ("no_yoy", {}))
    if m["spike_share"] > RULES["spike_driven_share"]:
        score -= RULES["pen_spike_driven"]
        reasons.append(("spikes", {"s": f"{m['spike_share']:.0%}"}))
    if m.get("divergence"):
        score -= RULES["pen_divergence"]
        reasons.append(("divergence", {}))
    if m.get("agreement") is not None and m["n_articles"] > 2 and m["agreement"] < RULES["low_breadth"]:
        score -= RULES["pen_low_breadth"]
        reasons.append(("breadth", {"b": f"{m['agreement']:.0%}"}))
    if m.get("bot_suspect"):
        score -= RULES["pen_bot"]
        reasons.append(("bot", {}))
    if m.get("late_start"):
        score -= RULES["pen_late_start"]
        reasons.append(("late", {}))

    score = max(0, score)
    level = _level(score)
    capped = LEVELS.index(cap) < LEVELS.index(level)
    if capped:
        level = cap
    else:
        reasons += caps
        caps = []
    if not reasons and not caps:
        reasons.append(("ok", {}))
    return {"level": level, "score": score, "_caps": caps, "_reasons": reasons}


def render(c: dict, out: str) -> dict:
    """Add human text in language `out`: label, reasons, capped_by."""
    fmt = lambda items: [REASONS[code][out].format(**kw) for code, kw in items]  # noqa: E731
    caps = fmt(c["_caps"])
    label = f"{LEVEL_NAMES[out][c['level']]} ({c['score']}/10" + (f", {CAPPED[out]}: " + "; ".join(caps) if caps else "") + ")"
    return {"level": c["level"], "score": c["score"], "label": label, "capped_by": caps, "reasons": fmt(c["_reasons"])}
