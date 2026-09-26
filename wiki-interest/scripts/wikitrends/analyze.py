"""Per-language analysis of a basket. Pure function of already-fetched data,
so it is tested on synthetic inputs without network (tests/test_analyze.py).

Flow of `analyze_language`:
  every article: daily views -> spikes removed -> monthly raw / clean
  basket:        sum of articles / views of the whole edition = share (ppm)
  metrics:       YoY growth + consistency -> direction; seasonality; trend;
                 level shift; stability; agreement of articles; bot signal
  confidence:    rules in confidence.py
"""
from __future__ import annotations

import numpy as np

from . import confidence, months as M, stats
from .config import RULES


def analyze_language(lang: str, fetch_months: list[str], analysis_months: list[str], articles: list[dict],
                     project: dict[str, int], main_desktop: dict[str, int] | None = None,
                     project_desktop: dict[str, int] | None = None) -> dict:
    """articles: [{qid, label, title, daily: {date: views}, proxy: bool, main: bool}]"""
    dates = [d for m in fetch_months for d in M.day_list(m)]
    period = min(12, len(analysis_months))
    proj = np.array([project.get(m, 0) for m in fetch_months], dtype=float)
    proj_safe = np.where(proj > 0, proj, np.nan)  # avoid division by zero

    # --- articles -> basket totals
    raw_total = np.zeros(len(fetch_months))
    clean_total = np.zeros(len(fetch_months))
    per_article, spikes, late = [], {}, []
    seasonal_spike_months: set[int] = set()
    main_spike_days: list[str] = []
    for a in articles:
        art = _article(a, dates, fetch_months, proj_safe, period)
        raw_total += art["raw"]
        clean_total += art["clean"]
        spikes[a["title"]] = art["spike_days"]
        seasonal_spike_months |= art["seasonal_months"]
        if a.get("main"):
            main_spike_days = sorted(art["spike_days"])
        if art["late"]:
            late.append(art["late"])
        per_article.append(art["summary"])

    # --- growth and direction on the topic's share of the edition
    share_raw = np.nan_to_num(raw_total / proj_safe * 1e6)
    share_clean = np.nan_to_num(clean_total / proj_safe * 1e6)
    y_clean = stats.yoy(share_clean, period)
    direction = stats.direction(y_clean["growth"], y_clean["k"], y_clean["n"], y_clean["p"])
    med_g, breadth = stats.median_growth([p["growth_clean"] for p in per_article if p["has_data"]])
    divergence = bool(y_clean["growth"] is not None and y_clean["growth"] > RULES["flat_band"]
                      and med_g is not None and med_g <= 0 and len(per_article) > 2)

    # --- shape of the series
    season = stats.seasonality(fetch_months, share_clean)
    first_analysed = fetch_months.index(analysis_months[0])
    deseason = _deseasonalised(fetch_months, share_clean, season)
    cv, stability = _stability(deseason[first_analysed:])
    first_nonzero = np.nonzero(raw_total)[0]
    a_idx = [fetch_months.index(m) for m in analysis_months]
    bot, bot_detail = _bot_signal(articles, main_desktop, project_desktop, project, analysis_months, main_spike_days)

    m = {
        "lang": lang,
        "direction": direction,
        "growth_clean": y_clean["growth"],
        "growth_raw_share": stats.yoy(share_raw, period)["growth"],
        "growth_views": stats.yoy(raw_total, period)["growth"],
        "project_growth": stats.yoy(proj, period)["growth"],
        "k": y_clean["k"], "n": y_clean["n"], "p": y_clean["p"],
        "period_months": period,
        "spike_share": stats.spike_share_of_growth(share_raw, share_clean, period),
        "median_article_growth": med_g,
        "breadth": breadth,
        "agreement": _agreement(y_clean["growth"], per_article),
        "divergence": divergence,
        "stability": stability, "cv": cv,
        "n_articles": sum(p["has_data"] for p in per_article),
        "share_ppm": float(np.mean(share_clean[-period:])) if period else 0.0,
        "views_12m": float(np.sum(raw_total[-12:])),
        "median_monthly_views": float(np.median(raw_total[a_idx])) if a_idx else 0.0,
        "history_months": int(len(fetch_months) - first_nonzero[0]) if len(first_nonzero) else 0,
        "late_start": _material(late, raw_total),
        "proxy": any(a.get("proxy") for a in articles),
        "bot_suspect": bot, "bot_detail": bot_detail,
        "season": season,
        "seasonal_spike_months": sorted(seasonal_spike_months),
        "trend_annual": stats.theil_sen_annual(fetch_months, share_clean, season),
        "level_shift": _level_shift(deseason[first_analysed:], analysis_months),
        "news_events": _news_events(spikes, {a["title"]: a.get("label", a["title"]) for a in articles})[:5],
        "spike_days": sum(len(v) for v in spikes.values()),
        "articles": per_article,
        "series": {"months": fetch_months, "share_clean": share_clean.round(3).tolist(),
                   "share_raw": share_raw.round(3).tolist(), "views_raw": raw_total.tolist(),
                   "project": proj.tolist()},
    }
    m["confidence_raw"] = confidence.assess(m)
    m["confidence"] = confidence.render(m["confidence_raw"], "en")
    return m


# ---------- one article ----------

def _article(a: dict, dates: list[str], fetch_months: list[str], proj_safe: np.ndarray, period: int) -> dict:
    """Spike-clean one article and aggregate it to months."""
    x = np.array([a["daily"].get(d, 0) for d in dates], dtype=float)
    cleaned, mask, seasonal_months = stats.clean_spikes(dates, x)
    raw = monthly(x, dates, fetch_months)
    clean = monthly(cleaned, dates, fetch_months)
    nonzero = np.nonzero(raw)[0]
    first = int(nonzero[0]) if len(nonzero) else None
    late = None
    if first is not None and first >= 2:  # the article appeared during the downloaded period
        late = {"title": a["title"], "first_month": fetch_months[first], "views_12m": float(np.sum(raw[-12:]))}
    growth = stats.yoy(np.nan_to_num(clean / proj_safe), period)["growth"]
    summary = {"qid": a["qid"], "title": a["title"], "label": a.get("label", a["title"]),
               "growth_clean": growth, "views_12m": float(np.sum(raw[-12:])),
               "proxy": bool(a.get("proxy")), "has_data": first is not None}
    return {"raw": raw, "clean": clean, "spike_days": {d for d, s in zip(dates, mask) if s},
            "seasonal_months": seasonal_months, "late": late, "summary": summary}


def monthly(daily_vals: np.ndarray, dates: list[str], months: list[str]) -> np.ndarray:
    """Sum daily values into the given months (days outside them are ignored)."""
    idx = {m: i for i, m in enumerate(months)}
    out = np.zeros(len(months))
    for d, v in zip(dates, daily_vals):
        i = idx.get(d[:7])
        if i is not None:
            out[i] += v
    return out


# ---------- basket-level metrics ----------

def _agreement(topic_growth: float | None, per_article: list[dict]) -> float | None:
    """Share of articles moving the same way as the topic (only meaningful when
    the topic moves); low agreement = growth/decline of a few pages."""
    growths = [p["growth_clean"] for p in per_article if p["has_data"] and p["growth_clean"] is not None]
    if topic_growth is None or abs(topic_growth) <= RULES["flat_band"] or not growths:
        return None
    sign = 1 if topic_growth > 0 else -1
    return float(np.mean([g * sign > 0 for g in growths]))


def _material(late: list[dict], raw_total: np.ndarray) -> list[dict]:
    """A late article matters only if it is >= 5% of the basket's recent views."""
    total_12m = float(np.sum(raw_total[-12:])) or 1.0
    return [x for x in late if x["views_12m"] / total_12m >= 0.05]


def _deseasonalised(fetch_months: list[str], series: np.ndarray, season: dict | None) -> np.ndarray:
    """Divide by the seasonal index, but only when seasonality was actually detected."""
    seasonal = bool(season and (season["peaks"] or season["troughs"]))
    index = season["index"] if seasonal else {i: 1.0 for i in range(1, 13)}
    return np.array([v / max(index[int(mo[5:7])], 1e-9) for mo, v in zip(fetch_months, series)])


def _level_shift(window: np.ndarray, analysis_months: list[str]) -> dict | None:
    """Sharp step in the deseasonalised share (a school-year summer drop is not a
    technical break); reported when the level changes >= 1.6x or <= 0.6x."""
    shift = stats.level_shift(window)
    if shift and (shift["ratio"] >= 1.6 or shift["ratio"] <= 0.6):
        return {"month": analysis_months[shift["at"]], "ratio": shift["ratio"]}
    return None


def _stability(window: np.ndarray) -> tuple[float | None, float | None]:
    """(coefficient of variation, stability = 1/(1+CV)) of the deseasonalised
    share in the analysis window: predictability of demand, used in ranking."""
    if len(window) > 1 and np.mean(window) > 0:
        cv = float(np.std(window) / np.mean(window))
        return cv, 1 / (1 + cv)
    return None, None


def _bot_signal(articles: list[dict], main_desktop: dict | None, project_desktop: dict | None, project: dict,
                analysis_months: list[str], main_spike_days: list[str]) -> tuple[bool, dict | None]:
    """Possible automated traffic on the main article: its desktop share is far
    above the edition's, or its spike days are almost all desktop."""
    if main_desktop is None or project_desktop is None:
        return False, None
    main = next((a for a in articles if a.get("main")), None)
    if not main:
        return False, None
    days = [d for m in analysis_months for d in M.day_list(m)]
    total = sum(main["daily"].get(d, 0) for d in days)
    desktop = sum(main_desktop.get(d, 0) for d in days)
    p_total = sum(project.get(m, 0) for m in analysis_months)
    p_desktop = sum(project_desktop.get(m, 0) for m in analysis_months)
    if total <= 0 or p_total <= 0:
        return False, None
    article_share, project_share = desktop / total, p_desktop / p_total
    spike_desktop = [main_desktop.get(d, 0) / max(main["daily"].get(d, 0), 1) for d in main_spike_days]
    spikes_desktopish = bool(spike_desktop) and float(np.mean(spike_desktop)) >= RULES["bot_spike_desktop"]
    suspect = (article_share - project_share) > RULES["bot_desktop_pp"] or spikes_desktopish
    detail = {"article_desktop_share": article_share, "project_desktop_share": project_share,
              "spike_days_desktop_share": float(np.mean(spike_desktop)) if spike_desktop else None}
    return suspect, detail


def _news_events(spikes: dict[str, set[str]], labels: dict[str, str]) -> list[dict]:
    """Days when >= 2 basket articles spike within +-1 day -> news-driven event."""
    day_to_titles: dict[str, set[str]] = {}
    for title, days in spikes.items():
        for d in days:
            day_to_titles.setdefault(d, set()).add(title)
    events = []
    for d in sorted(day_to_titles):
        near = set()
        for other, ts in day_to_titles.items():
            if abs(np.datetime64(other) - np.datetime64(d)).astype(int) <= 1:
                near |= ts
        if len(near) >= 2 and not any(abs(np.datetime64(e["date"]) - np.datetime64(d)).astype(int) <= 3 for e in events):
            events.append({"date": d, "articles": sorted(labels.get(t, t) for t in near)[:4]})
    return events
