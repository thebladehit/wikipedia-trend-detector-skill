"""`run`: resolve -> basket -> fetch (cache) -> analyse -> verdicts -> files.

The agent only turns the request into parameters and retells the compact
JSON produced here; all decisions (direction, confidence, ranking) are made
in code."""
from __future__ import annotations

import datetime as dt
import json

from . import basket as B, charts, months as M, pageviews as PV, rank as R, resolve as RS, study as S, verdicts as V, wiki
from .analyze import analyze_language
from .config import METHODOLOGY_VERSION, RULES, TOOL_VERSION, WIT
from .confidence import render
from .http import STATS, WitError


def texts_language(user_lang: str) -> str:
    """Ready texts exist in Ukrainian and English; any other user language gets English texts."""
    return user_lang if user_lang in ("uk", "en") else "en"


def default_params() -> dict:
    return {"topic": None, "qid": None, "langs": [], "months": 24, "basket": "auto", "basket_size": RULES["basket_size"],
            "basket_add": [], "basket_remove": [], "articles": {}, "weights": None, "out": None, "end": None}


def run(params: dict, study_id: str | None = None) -> dict:
    p, langs, out = _checked_params(params)
    weights = R.parse_weights(p["weights"])
    warnings: list[dict] = []
    assumptions: list[str] = []
    texts = V.ASSUMPTIONS[out]

    # 1. topic -> Wikidata item
    res = RS.resolve(p["topic"], langs, qid=p["qid"], out=out)
    if res["status"] != "ok":
        return res
    ent = res["entity"]
    p["qid"] = ent["qid"]
    topic_label = wiki.label(ent, out)
    if res.get("interpreted"):
        warnings.append(_interpreted_warning(p["topic"], ent, topic_label, langs, out))

    # 2. main article per language (+ manual / proxy articles)
    main_titles, missing, proxies = _main_articles(ent, langs, p["articles"] or {})
    warnings += _article_warnings(missing, proxies, ent, topic_label)
    active = [l for l in langs if l in main_titles]
    if not active:
        return _no_article(ent, topic_label, langs)

    # 3. period
    months = max(1, int(p["months"]))
    fetch_months, analysis_months, notes = M.window(months, end=p["end"], extra=max(12, 36 - months))
    assumptions += [texts[code].format(**kw) for code, kw in notes]
    assumptions.append(texts["period"].format(a=analysis_months[0], b=analysis_months[-1], n=len(analysis_months),
                                              f=fetch_months[0]))
    if months < 12:
        assumptions.append(texts["short"].format(n=months))

    # 4. traffic of each edition: the normalisation base and its desktop share
    project = dict(zip(active, PV.fetch_many([(PV.project_monthly, l, fetch_months) for l in active])))
    project_desktop = dict(zip(active, PV.fetch_many([(PV.project_monthly, l, fetch_months, "desktop") for l in active])))

    # 5. basket of related articles
    items, basket_meta, removed, basket_warnings, basket_note = _basket(p, ent, active, project, proxies, main_titles, out)
    warnings += basket_warnings
    assumptions.append(basket_note)

    # 6. daily views (+ redirects and desktop views of the main article)
    views, redirects = _fetch_views(active, items, main_titles, fetch_months)
    assumptions.append(texts["views"].format(r=RULES["redirects_per_article"]))

    # 7. analyse each language, rank them
    results = {lang: _analyse(lang, items, views, redirects, main_titles, proxies, fetch_months, analysis_months,
                              project, project_desktop, out)
               for lang in active}
    ranking = R.rank([_rank_input(l, m) for l, m in results.items()], weights)
    if ranking:
        assumptions.append(texts["weights"].format(
            g=weights["growth"], s=weights["size"], st=weights["stability"],
            gp=f"{weights['growth']:.0%}", sp=f"{weights['size']:.0%}", stp=f"{weights['stability']:.0%}"))
    warnings += _language_warnings(results, out)

    # 8. save the study version and return the compact answer
    sid = study_id or f"{S.slug(wiki.label(ent, 'en'))}_{ent['qid']}"
    version, vdir = S.new_version(sid)
    for w in warnings:
        w["next"] = w["next"].replace("<id>", sid)
    readers = _readers(active, analysis_months[-1], out)
    chart_path = vdir / "chart.png"
    charts.plot(results, fetch_months, analysis_months, topic_label, chart_path, out, ranking)

    compact = {
        "status": "ok",
        "study": sid, "version": version,
        "texts_language": out if out == p["out"] else f"{out} (translate words into '{p['out']}', keep every number exactly)",
        "topic": {"label": topic_label, "qid": ent["qid"], "description": wiki.description(ent, out), "how": res["how"]},
        "period": {"from": analysis_months[0], "to": analysis_months[-1], "months": len(analysis_months)},
        "verdicts": {l: V.verdict(m, out) for l, m in results.items()},
        "trust": {l: V.trust(m, out) for l, m in results.items()},
        "must_mention": V.must_mention(results, missing, out) + V.basket_note(items, out),
        "readers": {"month": analysis_months[-1], "top_countries": readers, "note": V.READERS_NOTE[out]},
        "ranking": [{"lang": r["key"], "rank": r["rank"], "score": r["score"], "why": V.why(r, results[r["key"]], out)}
                    for r in ranking],
        "table_md": V.table_md(results, ranking, out),
        "basket": {"size": len(items), "shown": [it["label"] for it in items[:6]], "more": max(0, len(items) - 6),
                   "removed": sorted(removed)},
        "warnings": warnings,
        "assumptions": assumptions,
        "limitations": V.LIMITATIONS[out],
        "missing_languages": missing,
        "files": {"analysis": str(vdir / "analysis.json"), "chart": str(chart_path)},
        "next_steps": [
            f"PDF report: {WIT} report --study {sid} --summary \"<2-4 sentences using only numbers above>\"",
            f"Change languages/period/basket/weights: {WIT} edit --study {sid} --add-langs sk --months 36 --weights growth=0.2,size=0.3,stability=0.5",
        ],
        "api": {"requests_made": STATS["requests_made"], "cache_hits": STATS["cache_hits"]},
    }
    full = {
        "tool_version": TOOL_VERSION, "methodology_version": METHODOLOGY_VERSION,
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "params": p, "rules": RULES, "weights": weights, "entity": ent,
        "basket": items, "basket_meta": basket_meta, "redirects": {f"{k[0]}:{k[1]}": v for k, v in redirects.items()},
        "results": {l: {k: v for k, v in m.items() if k != "confidence_raw"} for l, m in results.items()},
        "ranking": ranking, "compact": compact,
    }
    (vdir / "analysis.json").write_text(json.dumps(full, ensure_ascii=False, indent=1, default=float))
    (vdir / "summary.json").write_text(json.dumps(compact, ensure_ascii=False, indent=1))
    S.save(sid, p, version, {"topic_label": topic_label})
    return compact


# ---------- 0. parameters ----------

def _checked_params(params: dict) -> tuple[dict, list[str], str]:
    """Fill defaults and validate. Returns (params, languages, texts language)."""
    p = {**default_params(), **params}
    langs = [l.strip().lower() for l in p["langs"] if l.strip()]
    if not langs:
        raise WitError("bad_args", "No languages given", "Pass --langs uk,pl (Wikipedia language codes).")
    if not p["out"]:
        raise WitError("bad_args", "No --out given", "Pass --out <code of the user's language>, e.g. --out uk.")
    p["out"] = p["out"].strip().lower()
    out = texts_language(p["out"])
    p["texts"] = out
    return p, langs, out


# ---------- 1–2. topic and main articles ----------

def _interpreted_warning(topic: str, ent: dict, label: str, langs: list[str], out: str) -> dict:
    return {"code": "topic_interpreted",
            "text": f"No exact match for '{topic}'; using the closest Wikidata item: {label} ({ent['qid']}) — {wiki.description(ent, out)}.",
            "next": f"If this is wrong: {WIT} resolve --topic \"...\" --langs {','.join(langs)} and rerun with --qid"}


def _main_articles(ent: dict, langs: list[str], manual: dict[str, str]) -> tuple[dict, list[str], dict]:
    """Main article title per language. Articles given by the user replace the
    missing/default ones; if they are a different Wikidata item they are proxies.
    Returns (titles, languages without an article, proxies)."""
    titles, missing = RS.titles_for(ent, langs)
    proxies = {}
    for lang, title in manual.items():
        page = wiki.pageprops(lang, [title]).get(title, {})
        if not page or page.get("missing"):
            raise WitError("article_not_found", f"Article '{title}' not found in {lang} Wikipedia",
                           f"Check the exact title, e.g. on https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}")
        titles[lang] = page["title"]
        if lang in missing:
            missing.remove(lang)
        if page.get("qid") != ent["qid"]:
            proxies[lang] = page["title"]
    return titles, missing, proxies


def _article_warnings(missing: list[str], proxies: dict[str, str], ent: dict, label: str) -> list[dict]:
    warnings = [{"code": "missing_article",
                 "text": f"{lang}: no Wikipedia article for {label} ({ent['qid']}). Nothing is substituted automatically.",
                 "next": f"To measure a related article instead (marked as proxy): {WIT} edit --study <id> --article {lang}:\"<Title>\""}
                for lang in missing]
    warnings += [{"code": "proxy_article",
                  "text": f"{lang}: '{title}' is a different Wikidata item than {ent['qid']} — it is a proxy; confidence is capped at medium.",
                  "next": "Mention in the answer that this language measures a related concept."}
                 for lang, title in proxies.items()]
    return warnings


def _no_article(ent: dict, label: str, langs: list[str]) -> dict:
    return {"status": "needs_input", "reason": "no_article",
            "question": f"None of {', '.join(langs)} has an article about {label}. Pick other languages or give an article per language.",
            "options": [], "next": f"{WIT} run --qid {ent['qid']} --langs {','.join(langs)} --article {langs[0]}:\"<Title>\""}


# ---------- 5. basket ----------

def _basket(p: dict, ent: dict, active: list[str], project: dict, proxies: dict, main_titles: dict, out: str):
    """Returns (items, meta, removed labels, warnings, assumption sentence)."""
    texts = V.ASSUMPTIONS[out]
    warnings: list[dict] = []
    # candidates are discovered in English Wikipedia when it has the article
    # (richest links, best `morelike`), otherwise in the biggest compared edition
    largest = max(active, key=lambda l: sum(list(project[l].values())[-12:]) if l not in proxies else -1)
    discover = "en" if "en" in ent["sitelinks"] else largest
    if p["basket"] == "auto" and discover in ent["sitelinks"]:
        excluded = {r.upper() for r in p["basket_remove"] if r.upper().startswith("Q")}
        items, warnings, meta = B.build(ent, active, discover, out, p["basket_size"], exclude=excluded)
        note = texts["basket"].format(n=len(items), w=discover, m=meta.get("method"))
    else:
        items = [B.item(ent, active, out, "main topic article")]
        meta = {}
        note = texts["no_basket"]

    if p["basket_add"]:
        added, add_warnings = B.add_items(p["basket_add"], active, out)
        warnings += add_warnings
        have = {i["qid"] for i in items}
        items += [a for a in added if a["qid"] not in have]

    removed = set()
    if p["basket_remove"]:  # the main article itself is never removed
        main, rest = items[0], items[1:]
        dropped = [it for it in rest if any(B.matches(it, r) for r in p["basket_remove"])]
        removed = {it["label"] for it in dropped}
        items = [main] + [it for it in rest if it not in dropped]

    for lang, title in main_titles.items():  # manual/proxy main article
        items[0]["titles"][lang] = title
    return items, meta, removed, warnings, note


# ---------- 6. views ----------

def _fetch_views(active: list[str], items: list[dict], main_titles: dict, fetch_months: list[str]):
    """Download all daily series in parallel.
    Returns ({(lang, title, kind): {date: views}}, {(lang, article title): [redirects]}),
    kind = all | redirect | desktop."""
    jobs, keys = [], []
    redirects: dict[tuple[str, str], list[str]] = {}

    def add(lang, title, kind, access="all-access"):
        jobs.append((PV.article_daily, lang, title, fetch_months, access))
        keys.append((lang, title, kind))

    for lang in active:
        titles = [it["titles"][lang] for it in items if it["titles"].get(lang)]
        for title, top in _top_redirects(lang, titles).items():
            redirects[(lang, title)] = top
        for title in titles:
            add(lang, title, "all")
            for rd in redirects[(lang, title)]:
                add(lang, rd, "redirect")
        add(lang, main_titles[lang], "desktop", "desktop")
    return dict(zip(keys, PV.fetch_many(jobs))), redirects


def _top_redirects(lang: str, titles: list[str]) -> dict[str, list[str]]:
    """Up to `redirects_per_article` redirects per article that people actually
    use (most views in the last 60 days, zero-view ones skipped). Pageviews
    counts a redirect's views under the redirect title, not the article."""
    all_redirects = {t: wiki.redirects(lang, t) for t in titles}
    recent = wiki.recent_views(lang, [r for rds in all_redirects.values() for r in rds])
    top = {}
    for title, rds in all_redirects.items():
        used = sorted((r for r in rds if recent.get(r, 0) > 0), key=lambda r: -recent[r])
        top[title] = used[:RULES["redirects_per_article"]]
    return top


# ---------- 7. analysis ----------

def _analyse(lang, items, views, redirects, main_titles, proxies, fetch_months, analysis_months,
             project, project_desktop, out) -> dict:
    articles = []
    for n, it in enumerate(items):
        title = it["titles"].get(lang)
        if not title:
            continue
        daily = dict(views[(lang, title, "all")])
        for rd in redirects.get((lang, title), []):  # redirect views belong to the article
            for d, v in views[(lang, rd, "redirect")].items():
                daily[d] = daily.get(d, 0) + v
        articles.append({"qid": it["qid"], "label": it["label"], "title": title, "daily": daily, "main": n == 0,
                         "proxy": n == 0 and lang in proxies})
    m = analyze_language(lang, fetch_months, analysis_months, articles, project[lang],
                         views[(lang, main_titles[lang], "desktop")], project_desktop[lang])
    m["confidence"] = render(m["confidence_raw"], out)
    m["main_title"] = main_titles[lang]
    return m


def _rank_input(lang: str, m: dict) -> dict:
    return {"key": lang, "growth_clean": m["growth_clean"], "share_ppm": m["share_ppm"], "k": m["k"] or 0,
            "n": m["n"], "stability": m["stability"], "confidence": m["confidence"]["level"]}


def _language_warnings(results: dict, out: str) -> list[dict]:
    warnings = []
    for lang, m in results.items():
        if m["spike_share"] > RULES["spike_driven_share"]:
            warnings.append({"code": "spike_driven", "text": V.T[out]["spike"].format(lang=lang, s=f"{m['spike_share']:.0%}"),
                             "next": "Growth is reported on the cleaned series; mention that raw growth was inflated by spikes."})
        if m["bot_suspect"]:
            warnings.append({"code": "bot_suspect", "text": f"{lang}: unusual desktop share — possible automated traffic.",
                             "next": "Treat growth in this language with caution."})
        if m["late_start"]:
            warnings.append({"code": "article_history_starts_late",
                             "text": f"{lang}: " + ", ".join(f"{x['title']} (from {x['first_month']})" for x in m["late_start"][:3]),
                             "next": f"If this distorts the result: {WIT} edit --study <id> --basket-remove \"<Title>\""})
        if m["level_shift"]:
            shift = m["level_shift"]
            warnings.append({"code": "level_shift", "text": f"{lang}: sharp level change from {shift['month']} (x{shift['ratio']:.1f}).",
                             "next": "Check whether the article was renamed/merged; see chart."})
    return warnings


# ---------- 8. readers ----------

def _readers(active: list[str], month: str, out: str) -> dict[str, str]:
    """Top-3 reader countries per edition (bucketed, privacy-limited; rough shares only)."""
    readers = {}
    for lang, rows in zip(active, PV.fetch_many([(PV.project_countries, l, month) for l in active])):
        top = [r for r in rows if r["country"] != "--"][:3]
        if not top:
            continue
        # Wikimedia hides countries on its privacy protection list (verified:
        # rank 1 is missing for tr, vi, ru) -> shares of the visible rest
        # would be misleading, so show names only
        if any(r["rank"] != i + 1 for i, r in enumerate(rows[:3])):
            readers[lang] = V.READERS_HIDDEN[out].format(c=", ".join(r["country"] for r in top))
        else:
            readers[lang] = ", ".join(f"{r['country']} {r['share']:.0%}" for r in top)
    return readers
