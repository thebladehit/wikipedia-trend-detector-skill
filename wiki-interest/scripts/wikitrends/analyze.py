"""Per-language analysis of a basket. Pure function of already-fetched data,
so it is tested on synthetic inputs without network (tests/test_analyze.py)."""
from __future__ import annotations

import numpy as np

from . import confidence, months as M, stats
from .config import RULES


def monthly(daily_vals: np.ndarray, dates: list[str], months: list[str]) -> np.ndarray:
    idx = {m: i for i, m in enumerate(months)}
    out = np.zeros(len(months))
    for d, v in zip(dates, daily_vals):
        i = idx.get(d[:7])
        if i is not None:
            out[i] += v
    return out


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


def analyze_language(lang: str, fetch_months: list[str], analysis_months: list[str], articles: list[dict],
                     project: dict[str, int], main_desktop: dict[str, int] | None = None,
                     project_desktop: dict[str, int] | None = None) -> dict:
    """articles: [{qid, label, title, daily: {date: views}, proxy: bool, main: bool}]"""
    dates = [d for m in fetch_months for d in M.day_list(m)]
    n_f = len(fetch_months)
    period = min(12, len(analysis_months))
    proj = np.array([project.get(m, 0) for m in fetch_months], dtype=float)
    proj_safe = np.where(proj > 0, proj, np.nan)

    raw_total = np.zeros(n_f)
    clean_total = np.zeros(n_f)
    per_article = []
    spikes: dict[str, set[str]] = {}
    seasonal_spike_months: set[int] = set()
    late = []
    main_spike_days: list[str] = []
    for a in articles:
        x = np.array([a["daily"].get(d, 0) for d in dates], dtype=float)
        cleaned, mask, seas = stats.clean_spikes(dates, x)
        seasonal_spike_months |= seas
        raw_m = monthly(x, dates, fetch_months)
        clean_m = monthly(cleaned, dates, fetch_months)
        raw_total += raw_m
        clean_total += clean_m
        sd = {d for d, s in zip(dates, mask) if s}
        spikes[a["title"]] = sd
        if a.get("main"):
            main_spike_days = sorted(sd)
        nz = np.nonzero(raw_m)[0]
        first = int(nz[0]) if len(nz) else None
        if first is not None and first >= 2:
            late.append({"title": a["title"], "first_month": fetch_months[first], "views_12m": float(np.sum(raw_m[-12:]))})
        g = stats.yoy(np.nan_to_num(clean_m / proj_safe), period)
        per_article.append({"qid": a["qid"], "title": a["title"], "label": a.get("label", a["title"]),
                            "growth_clean": g["growth"], "views_12m": float(np.sum(raw_m[-12:])),
                            "proxy": bool(a.get("proxy")), "has_data": first is not None})

    share_raw = np.nan_to_num(raw_total / proj_safe * 1e6)
    share_clean = np.nan_to_num(clean_total / proj_safe * 1e6)
    y_clean = stats.yoy(share_clean, period)
    y_raw = stats.yoy(share_raw, period)
    y_views = stats.yoy(raw_total, period)
    y_proj = stats.yoy(proj, period)
    direction = stats.direction(y_clean["growth"], y_clean["k"], y_clean["n"], y_clean["p"])
    spike_share = stats.spike_share_of_growth(share_raw, share_clean, period)
    med_g, breadth = stats.median_growth([p["growth_clean"] for p in per_article if p["has_data"]])
    # agreement: share of articles moving the same way as the topic (only
    # meaningful when the topic moves); low agreement = growth/decline of a few pages
    g_all = [p["growth_clean"] for p in per_article if p["has_data"] and p["growth_clean"] is not None]
    agreement = None
    if y_clean["growth"] is not None and abs(y_clean["growth"]) > RULES["flat_band"] and g_all:
        sign = 1 if y_clean["growth"] > 0 else -1
        agreement = float(np.mean([g * sign > 0 for g in g_all]))
    # a late article matters only if it is a material part of the basket
    total_12m = float(np.sum(raw_total[-12:])) or 1.0
    late = [x for x in late if x["views_12m"] / total_12m >= 0.05]
    divergence = bool(y_clean["growth"] is not None and y_clean["growth"] > RULES["flat_band"]
                      and med_g is not None and med_g <= 0 and len(per_article) > 2)
    season = stats.seasonality(fetch_months, share_clean)
    trend = stats.theil_sen_annual(fetch_months, share_clean, season)

    a_idx = [fetch_months.index(m) for m in analysis_months]
    # level shifts are searched on the deseasonalised series: a school-year
    # pattern (summer drop) is not a technical break
    seasonal = bool(season and (season["peaks"] or season["troughs"]))
    s_idx = season["index"] if seasonal else {i: 1.0 for i in range(1, 13)}
    deseason = np.array([v / max(s_idx[int(mo[5:7])], 1e-9) for mo, v in zip(fetch_months, share_clean)])
    shift = stats.level_shift(deseason[a_idx[0]:])
    level_shift = None
    if shift and (shift["ratio"] >= 1.6 or shift["ratio"] <= 0.6):
        level_shift = {"month": analysis_months[shift["at"]], "ratio": shift["ratio"]}

    # stability for ranking = predictability of demand: low month-to-month
    # variation of the deseasonalised share inside the analysis window
    win = deseason[a_idx[0]:]
    cv = float(np.std(win) / np.mean(win)) if len(win) > 1 and np.mean(win) > 0 else None
    stability = None if cv is None else 1 / (1 + cv)

    first_nz = np.nonzero(raw_total)[0]
    history = int(n_f - first_nz[0]) if len(first_nz) else 0
    median_views = float(np.median(raw_total[a_idx])) if a_idx else 0.0

    bot = False
    bot_detail = None
    if main_desktop is not None and project_desktop is not None:
        main = next((a for a in articles if a.get("main")), None)
        if main:
            a_dates = [d for m in analysis_months for d in M.day_list(m)]
            tot = sum(main["daily"].get(d, 0) for d in a_dates)
            desk = sum(main_desktop.get(d, 0) for d in a_dates)
            p_tot = sum(project.get(m, 0) for m in analysis_months)
            p_desk = sum(project_desktop.get(m, 0) for m in analysis_months)
            if tot > 0 and p_tot > 0:
                a_share, p_share = desk / tot, p_desk / p_tot
                spike_desk = [main_desktop.get(d, 0) / max(main["daily"].get(d, 0), 1) for d in main_spike_days]
                spike_desktopish = bool(spike_desk) and float(np.mean(spike_desk)) >= RULES["bot_spike_desktop"]
                bot = (a_share - p_share) > RULES["bot_desktop_pp"] or spike_desktopish
                bot_detail = {"article_desktop_share": a_share, "project_desktop_share": p_share,
                              "spike_days_desktop_share": float(np.mean(spike_desk)) if spike_desk else None}

    labels = {a["title"]: a.get("label", a["title"]) for a in articles}
    m = {
        "lang": lang,
        "direction": direction,
        "growth_clean": y_clean["growth"],
        "growth_raw_share": y_raw["growth"],
        "growth_views": y_views["growth"],
        "project_growth": y_proj["growth"],
        "k": y_clean["k"], "n": y_clean["n"], "p": y_clean["p"],
        "period_months": period,
        "spike_share": spike_share,
        "median_article_growth": med_g,
        "breadth": breadth,
        "agreement": agreement,
        "divergence": divergence,
        "stability": stability, "cv": cv,
        "n_articles": sum(p["has_data"] for p in per_article),
        "share_ppm": float(np.mean(share_clean[-period:])) if period else 0.0,
        "views_12m": float(np.sum(raw_total[-12:])),
        "median_monthly_views": median_views,
        "history_months": history,
        "late_start": late,
        "proxy": any(a.get("proxy") for a in articles),
        "bot_suspect": bot, "bot_detail": bot_detail,
        "season": season,
        "seasonal_spike_months": sorted(seasonal_spike_months),
        "trend_annual": trend,
        "level_shift": level_shift,
        "news_events": _news_events(spikes, labels)[:5],
        "spike_days": sum(len(v) for v in spikes.values()),
        "articles": per_article,
        "series": {"months": fetch_months, "share_clean": share_clean.round(3).tolist(),
                   "share_raw": share_raw.round(3).tolist(), "views_raw": raw_total.tolist(),
                   "project": proj.tolist()},
    }
    m["confidence_raw"] = confidence.assess(m)
    m["confidence"] = confidence.render(m["confidence_raw"], "en")
    return m
