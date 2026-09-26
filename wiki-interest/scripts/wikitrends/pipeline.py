"""`run`: resolve -> basket -> fetch (cache) -> analyse -> verdicts -> files.

The agent only turns the request into parameters and retells the compact
JSON produced here; all decisions (direction, confidence, ranking) are made
in code."""
from __future__ import annotations

import datetime as dt
import json

from . import basket as B, charts, months as M, pageviews as PV, rank as R, resolve as RS, study as S, verdicts as V, wiki
from .config import METHODOLOGY_VERSION, RULES, SKILL_DIR, TOOL_VERSION
from .confidence import render
from .http import STATS, WitError

WIT = f'uv run "{SKILL_DIR}/scripts/wit.py"'


def _r(x, nd=3):
    return None if x is None else round(float(x), nd)


def texts_language(user_lang: str) -> str:
    """Ready texts exist in Ukrainian and English; any other user language gets English texts."""
    return user_lang if user_lang in ("uk", "en") else "en"


def default_params() -> dict:
    return {"topic": None, "qid": None, "langs": [], "months": 24, "basket": "auto", "basket_size": RULES["basket_size"],
            "basket_add": [], "basket_remove": [], "articles": {}, "weights": None, "out": None, "end": None}


def run(params: dict, study_id: str | None = None) -> dict:
    p = {**default_params(), **params}
    langs = [l.strip().lower() for l in p["langs"] if l.strip()]
    if not langs:
        raise WitError("bad_args", "No languages given", "Pass --langs uk,pl (Wikipedia language codes).")
    if not p["out"]:
        raise WitError("bad_args", "No --out given", "Pass --out <code of the user's language>, e.g. --out uk.")
    p["out"] = p["out"].strip().lower()
    out = texts_language(p["out"])
    p["texts"] = out
    weights = R.parse_weights(p["weights"])

    # 1. topic -> Wikidata item
    res = RS.resolve(p["topic"], langs, qid=p["qid"], out=out)
    if res["status"] != "ok":
        return res
    ent = res["entity"]
    p["qid"] = ent["qid"]
    topic_label = wiki.label(ent, out)
    assumptions, warnings = [], []
    if res.get("interpreted"):
        warnings.append({"code": "topic_interpreted",
                         "text": f"No exact match for '{p['topic']}'; using the closest Wikidata item: {topic_label} ({ent['qid']}) — {wiki.description(ent, out)}.",
                         "next": f"If this is wrong: {WIT} resolve --topic \"...\" --langs {','.join(langs)} and rerun with --qid"})

    # 2. main article per language (+ manual / proxy articles)
    main_titles, missing = RS.titles_for(ent, langs)
    proxies = {}
    for lang, title in (p["articles"] or {}).items():
        pp = wiki.pageprops(lang, [title]).get(title, {})
        if not pp or pp.get("missing"):
            raise WitError("article_not_found", f"Article '{title}' not found in {lang} Wikipedia",
                           f"Check the exact title, e.g. on https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}")
        main_titles[lang] = pp["title"]
        if lang in missing:
            missing.remove(lang)
        if pp.get("qid") != ent["qid"]:
            proxies[lang] = pp["title"]
    for lang in missing:
        warnings.append({"code": "missing_article",
                         "text": f"{lang}: no Wikipedia article for {topic_label} ({ent['qid']}). Nothing is substituted automatically.",
                         "next": f"To measure a related article instead (marked as proxy): {WIT} edit --study <id> --article {lang}:\"<Title>\""})
    for lang, t in proxies.items():
        warnings.append({"code": "proxy_article",
                         "text": f"{lang}: '{t}' is a different Wikidata item than {ent['qid']} — it is a proxy; confidence is capped at medium.",
                         "next": "Mention in the answer that this language measures a related concept."})
    active = [l for l in langs if l in main_titles]
    if not active:
        return {"status": "needs_input", "reason": "no_article",
                "question": f"None of {', '.join(langs)} has an article about {topic_label}. Pick other languages or give an article per language.",
                "options": [], "next": f"{WIT} run --qid {ent['qid']} --langs {','.join(langs)} --article {langs[0]}:\"<Title>\""}

    # 3. period
    months = max(1, int(p["months"]))
    fetch_months, analysis_months, notes = M.window(months, end=p["end"], extra=max(12, 36 - months))
    A = V.ASSUMPTIONS[out]
    assumptions += [A[code].format(**kw) for code, kw in notes]
    assumptions.append(A["period"].format(a=analysis_months[0], b=analysis_months[-1], n=len(analysis_months), f=fetch_months[0]))
    if months < 12:
        assumptions.append(A["short"].format(n=months))

    # 4. project traffic (normalisation base) and desktop share
    proj = dict(zip(active, PV.fetch_many([(PV.project_monthly, l, fetch_months) for l in active])))
    proj_desk = dict(zip(active, PV.fetch_many([(PV.project_monthly, l, fetch_months, "desktop") for l in active])))
    pivot = max(active, key=lambda l: sum(list(proj[l].values())[-12:]) if l not in proxies else -1)

    # 5. basket
    removed = set()
    items: list[dict]
    # candidates are discovered in English Wikipedia when it has the article
    # (richest links, best `morelike`), then filtered to the compared languages
    discover = "en" if "en" in ent["sitelinks"] else pivot
    if p["basket"] == "auto" and discover in ent["sitelinks"]:
        excl = {r.upper() for r in p["basket_remove"] if r.upper().startswith("Q")}
        items, bw = B.build(ent, active, discover, out, p["basket_size"], exclude=excl)
        meta = next((w["meta"] for w in bw if w["code"] == "_basket_meta"), {})
        warnings += [w for w in bw if w["code"] != "_basket_meta"]
        assumptions.append(A["basket"].format(n=len(items), w=discover, m=meta.get("method")))
    else:
        items = [B._item(ent, active, out, "main topic article")]
        meta = {}
        assumptions.append(A["no_basket"])
    if p["basket_add"]:
        added, aw = B.add_items(p["basket_add"], active, out)
        warnings += aw
        have = {i["qid"] for i in items}
        items += [a for a in added if a["qid"] not in have]
    if p["basket_remove"]:
        keep = []
        for it in items:
            if it is not items[0] and any(B.matches(it, r) for r in p["basket_remove"]):
                removed.add(it["label"])
            else:
                keep.append(it)
        items = keep
    for lang, t in main_titles.items():  # manual/proxy main article
        items[0]["titles"][lang] = t

    # 6. fetch daily views (+ redirects of the main article, + desktop of main)
    jobs, keys = [], []
    redirect_map: dict[tuple[str, str], list[str]] = {}
    for lang in active:
        rd = wiki.redirects(lang, main_titles[lang])[:RULES["redirects_per_main"]]
        redirect_map[(lang, main_titles[lang])] = rd
        for it in items:
            t = it["titles"].get(lang)
            if t:
                jobs.append((PV.article_daily, lang, t, fetch_months))
                keys.append((lang, t, "all"))
        for t in rd:
            jobs.append((PV.article_daily, lang, t, fetch_months))
            keys.append((lang, t, "redirect"))
        jobs.append((PV.article_daily, lang, main_titles[lang], fetch_months, "desktop"))
        keys.append((lang, main_titles[lang], "desktop"))
    data = dict(zip(keys, PV.fetch_many(jobs)))
    assumptions.append(A["views"].format(r=RULES["redirects_per_main"]))

    # 7. analyse each language
    from .analyze import analyze_language
    results = {}
    for lang in active:
        arts = []
        for n, it in enumerate(items):
            t = it["titles"].get(lang)
            if not t:
                continue
            daily = dict(data[(lang, t, "all")])
            if n == 0:
                for rt in redirect_map.get((lang, t), []):
                    for d, v in data[(lang, rt, "redirect")].items():
                        daily[d] = daily.get(d, 0) + v
            arts.append({"qid": it["qid"], "label": it["label"], "title": t, "daily": daily, "main": n == 0,
                         "proxy": n == 0 and lang in proxies})
        m = analyze_language(lang, fetch_months, analysis_months, arts, proj[lang],
                             data[(lang, main_titles[lang], "desktop")], proj_desk[lang])
        m["confidence"] = render(m["confidence_raw"], out)
        m["main_title"] = main_titles[lang]
        results[lang] = m

    # 8. ranking, verdicts, warnings
    ranking = R.rank([{"key": l, "growth_clean": m["growth_clean"], "share_ppm": m["share_ppm"], "k": m["k"] or 0,
                       "n": m["n"], "stability": m["stability"], "confidence": m["confidence"]["level"]} for l, m in results.items()], weights)
    if ranking:
        assumptions.append(A["weights"].format(g=weights["growth"], s=weights["size"], st=weights["stability"],
                                               gp=f"{weights['growth']:.0%}", sp=f"{weights['size']:.0%}",
                                               stp=f"{weights['stability']:.0%}"))
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
            warnings.append({"code": "level_shift", "text": f"{lang}: sharp level change from {m['level_shift']['month']} (x{m['level_shift']['ratio']:.1f}).",
                             "next": "Check whether the article was renamed/merged; see chart."})

    sid = study_id or f"{S.slug(wiki.label(ent, 'en'))}_{ent['qid']}"
    version, vdir = S.new_version(sid)
    for w in warnings:
        w["next"] = w["next"].replace("<id>", sid)

    # who reads each edition (bucketed, privacy-limited; rough shares only)
    readers = {}
    for lang, rows in zip(active, PV.fetch_many([(PV.project_countries, l, analysis_months[-1]) for l in active])):
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
    verdicts = {l: V.verdict(m, out) for l, m in results.items()}
    must = V.must_mention(results, missing, out)
    if len(items) > 1:
        shown = ", ".join(it["label"] for it in items[:5]) + (" …" if len(items) > 5 else "")
        must.append(V.T[out]["basket"].format(n=len(items), items=shown))
    rank_rows = [{"lang": r["key"], "rank": r["rank"], "score": r["score"], "why": V.why(r, results[r["key"]], out)}
                 for r in ranking]
    rank_of = {r["key"]: r["rank"] for r in ranking}
    hdr = {"uk": "| мова | частка теми, рік до року | перегляди | напрям | довіра | місце |",
           "en": "| language | topic share, YoY | views | direction | confidence | rank |"}[out]
    rows = [hdr, "|---|---|---|---|---|---|"]
    for l, m in sorted(results.items(), key=lambda kv: rank_of.get(kv[0], 0)):
        rows.append(f"| {l} | {V.pct(m['growth_clean'])} | {V.pct(m['growth_views'])} | {V.DIRECTION[out][m['direction']]} | "
                    f"{V.LEVEL[out][m['confidence']['level']]} ({m['confidence']['score']}/10) | {rank_of.get(l, '—')} |")
    table_md = "\n".join(rows)

    chart_path = vdir / "chart.png"
    charts.plot(results, fetch_months, analysis_months, topic_label, chart_path, out, ranking)

    basket_shown = [it["label"] for it in items[:6]]
    compact = {
        "status": "ok",
        "study": sid, "version": version,
        "texts_language": out if out == p["out"] else f"{out} (translate words into '{p['out']}', keep every number exactly)",
        "topic": {"label": topic_label, "qid": ent["qid"], "description": wiki.description(ent, out), "how": res["how"]},
        "period": {"from": analysis_months[0], "to": analysis_months[-1], "months": len(analysis_months)},
        "verdicts": verdicts,
        "trust": {l: V.trust(m, out) for l, m in results.items()},
        "must_mention": must,
        "readers": {"month": analysis_months[-1], "top_countries": readers,
                    "note": V.READERS_NOTE[out]},
        "ranking": rank_rows,
        "table_md": table_md,
        "basket": {"size": len(items), "shown": basket_shown, "more": max(0, len(items) - 6),
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
        "basket": items, "basket_meta": meta, "redirects": {f"{k[0]}:{k[1]}": v for k, v in redirect_map.items()},
        "results": {l: {k: v for k, v in m.items() if k != "confidence_raw"} for l, m in results.items()},
        "ranking": ranking, "compact": compact,
    }
    (vdir / "analysis.json").write_text(json.dumps(full, ensure_ascii=False, indent=1, default=float))
    (vdir / "summary.json").write_text(json.dumps(compact, ensure_ascii=False, indent=1))
    S.save(sid, p, version, {"topic_label": topic_label})
    return compact
