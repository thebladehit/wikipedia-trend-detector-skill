"""Basket of related articles: interest in a *topic*, not in one page.

Candidates: `morelike:` for the main article in the pivot language,
intersected with the main article's outgoing links (removes noise, see
API_NOTES). Candidates are validated by Wikidata (no disambiguation, lists,
years, papers; no people unless the topic is a person), kept only when they
exist in all target languages (fallback: in >= 50%), kept in relevance order;
generic hubs (> basket_hub_ratio x the main article's views) are dropped."""
from __future__ import annotations

import re

from . import wiki
from .config import RULES


def _item(ent: dict, langs: list[str], label_lang: str, reason: str, views: int | None = None) -> dict:
    return {"qid": ent["qid"], "label": wiki.label(ent, label_lang),
            "titles": {l: ent["sitelinks"][l] for l in langs if l in ent["sitelinks"]},
            "reason": reason, "views_60d": views}


def _stems(title: str) -> set[str]:
    return {w[:5].casefold() for w in re.findall(r"\w+", title) if len(w) >= 4}


def _distinctive_stems(main_title: str, pool: list[str]) -> set[str]:
    """Word stems of the main title that are not generic within the candidates
    ('language' in 'English language' appears in most candidates -> generic)."""
    out = set()
    for st in _stems(main_title):
        share = sum(st in _stems(t) for t in pool) / max(len(pool), 1)
        if share <= 0.3:
            out.add(st)
    return out


def build(entity: dict, langs: list[str], pivot: str, label_lang: str, size: int | None = None,
          exclude: set[str] | None = None) -> tuple[list[dict], list[dict]]:
    """Return (basket items incl. main, warnings)."""
    size = size or RULES["basket_size"]
    exclude = exclude or set()
    warnings: list[dict] = []
    main_title = entity["sitelinks"][pivot]
    main = _item(entity, langs, label_lang, "main topic article")

    cands = wiki.morelike(pivot, main_title, RULES["basket_candidates"])
    linked = wiki.links(pivot, main_title)
    inter = [c for c in cands if c in linked]
    how = "morelike ∩ links of the main article" if len(inter) >= RULES["basket_min_intersection"] else "morelike only"
    pool = inter if len(inter) >= RULES["basket_min_intersection"] else cands

    props = wiki.pageprops(pivot, pool)
    qids = [p["qid"] for p in props.values() if p["qid"] and not p["disambiguation"] and not p["missing"]]
    qids = [q for q in dict.fromkeys(qids) if q != entity["qid"] and q not in exclude]
    ents = wiki.entities(qids, langs + [label_lang])
    topic_is_person = wiki.HUMAN in entity["p31"]
    valid = [e for e in ents.values()
             if e["sitelinks"] and not (set(e["p31"]) & wiki.NON_TOPIC_P31)
             and (topic_is_person or wiki.HUMAN not in e["p31"])]

    target = [l for l in langs if l in entity["sitelinks"]]
    common = [e for e in valid if all(l in e["sitelinks"] for l in target)]
    if len(common) < RULES["basket_min_common"] and len(target) > 1:
        need = max(1, -(-len(target) // 2))
        common = [e for e in valid if sum(l in e["sitelinks"] for l in target) >= need]
        warnings.append({"code": "basket_partial",
                         "text": f"Few related articles exist in all {len(target)} languages; basket uses articles present in at least {need} of them. Each language is measured on the articles it has.",
                         "next": "Add or remove articles with `edit --study <id> --basket-add/--basket-remove`."})

    # keep relevance order (morelike rank); drop generic hubs that are far more
    # popular than the topic itself (e.g. "COVID-19" for a diet topic) — they
    # would dominate the basket sum and measure something else
    rank = {t: i for i, t in enumerate(pool)}
    title_of = {p["qid"]: t for t, p in props.items() if p["qid"]}
    stems = _distinctive_stems(main_title, pool)
    common.sort(key=lambda e: (0 if _stems(title_of.get(e["qid"], "")) & stems else 1,
                               rank.get(title_of.get(e["qid"], ""), 10 ** 6)))
    views = wiki.recent_views(pivot, [main_title] + [e["sitelinks"][pivot] for e in common if pivot in e["sitelinks"]])
    main_views = max(views.get(main_title, 0), 1)
    hubs = [e for e in common if views.get(e["sitelinks"].get(pivot, ""), 0) > RULES["basket_hub_ratio"] * main_views]
    common = [e for e in common if e not in hubs]
    chosen = [_item(e, langs, label_lang, f"related ({how}, relevance #{n + 1}), {views.get(e['sitelinks'].get(pivot, ''), 0)} views in {pivot} last 60 days",
                    views.get(e["sitelinks"].get(pivot, ""), 0)) for n, e in enumerate(common[:size - 1])]
    meta = {"pivot": pivot, "method": how, "candidates": len(pool), "validated": len(valid), "common": len(common),
            "hubs_dropped": [wiki.label(e, label_lang) for e in hubs]}
    return [main] + chosen, warnings + [{"code": "_basket_meta", "meta": meta}]


def add_items(refs: list[str], langs: list[str], label_lang: str) -> tuple[list[dict], list[dict]]:
    """Manual additions: QIDs or lang:Title."""
    items, warnings = [], []
    qids = []
    for r in refs:
        if ":" in r and not r.upper().startswith("Q"):
            lang, title = r.split(":", 1)
            pp = wiki.pageprops(lang, [title]).get(title, {})
            if not pp.get("qid"):
                warnings.append({"code": "article_not_found", "text": f"Article '{title}' not found in {lang} Wikipedia.",
                                 "next": "Check the exact title on Wikipedia."})
                continue
            qids.append(pp["qid"])
        else:
            qids.append(r.upper())
    ents = wiki.entities(qids, langs + [label_lang])
    for q in qids:
        if q in ents:
            items.append(_item(ents[q], langs, label_lang, "added manually"))
    return items, warnings


def matches(item: dict, ref: str) -> bool:
    ref_n = ref.casefold().replace("_", " ")
    if ":" in ref and not ref.upper().startswith("Q"):
        ref_n = ref_n.split(":", 1)[1]
    return (item["qid"].casefold() == ref_n or item["label"].casefold() == ref_n
            or any(t.casefold() == ref_n for t in item["titles"].values()))
