"""Basket of related articles: interest in a *topic*, not in one page.

Steps of `build`:
1. candidates  — `morelike:` for the main article, intersected with the main
                 article's outgoing links (removes noise, see API_NOTES);
2. validation  — Wikidata: no disambiguation, lists, years, papers; no people
                 unless the topic is a person;
3. coverage    — keep articles that exist in all compared languages
                 (fallback: in >= 50% of them, with a warning);
4. ordering    — relevance order, words shared with the topic title first;
5. hubs        — drop generic articles far more popular than the topic
                 (> basket_hub_ratio x the main article's views).
"""
from __future__ import annotations

import re

from . import wiki
from .config import RULES


def item(ent: dict, langs: list[str], label_lang: str, reason: str, views: int | None = None) -> dict:
    """One basket entry: the Wikidata item and its article title per language."""
    return {"qid": ent["qid"], "label": wiki.label(ent, label_lang),
            "titles": {l: ent["sitelinks"][l] for l in langs if l in ent["sitelinks"]},
            "reason": reason, "views_60d": views}


# ---------- building the basket ----------

def build(entity: dict, langs: list[str], pivot: str, label_lang: str, size: int | None = None,
          exclude: set[str] | None = None) -> tuple[list[dict], list[dict], dict]:
    """Return (basket items incl. the main article first, warnings, meta).

    `pivot` is the Wikipedia where candidates are discovered."""
    size = size or RULES["basket_size"]
    main_title = entity["sitelinks"][pivot]

    pool, method = _candidates(pivot, main_title)
    title_by_qid = {}
    valid = _validated(entity, langs, label_lang, pivot, pool, exclude or set(), title_by_qid)
    common, warnings = _in_compared_languages(entity, langs, valid)
    common = _by_relevance(common, pool, main_title, title_by_qid)
    views = wiki.recent_views(pivot, [main_title] + [e["sitelinks"][pivot] for e in common if pivot in e["sitelinks"]])
    common, hubs = _without_hubs(common, views, main_title, pivot)

    chosen = []
    for rank, ent in enumerate(common[:size - 1], start=1):
        v = views.get(ent["sitelinks"].get(pivot, ""), 0)
        chosen.append(item(ent, langs, label_lang,
                           f"related ({method}, relevance #{rank}), {v} views in {pivot} last 60 days", v))
    meta = {"pivot": pivot, "method": method, "candidates": len(pool), "validated": len(valid), "common": len(common),
            "hubs_dropped": [wiki.label(e, label_lang) for e in hubs]}
    main = item(entity, langs, label_lang, "main topic article")
    return [main] + chosen, warnings, meta


def _candidates(pivot: str, main_title: str) -> tuple[list[str], str]:
    """Titles similar to the main article, in relevance order, and the method used."""
    similar = wiki.morelike(pivot, main_title, RULES["basket_candidates"])
    linked = wiki.links(pivot, main_title)
    both = [t for t in similar if t in linked]
    if len(both) >= RULES["basket_min_intersection"]:
        return both, "morelike ∩ links of the main article"
    return similar, "morelike only"


def _validated(entity: dict, langs: list[str], label_lang: str, pivot: str, pool: list[str],
               exclude: set[str], title_by_qid: dict[str, str]) -> list[dict]:
    """Wikidata items of the candidates that are real topics. Fills title_by_qid."""
    props = wiki.pageprops(pivot, pool)
    title_by_qid.update({p["qid"]: t for t, p in props.items() if p["qid"]})
    qids = [p["qid"] for p in props.values() if p["qid"] and not p["disambiguation"] and not p["missing"]]
    qids = [q for q in dict.fromkeys(qids) if q != entity["qid"] and q not in exclude]
    topic_is_person = wiki.HUMAN in entity["p31"]
    return [e for e in wiki.entities(qids, langs + [label_lang]).values()
            if e["sitelinks"] and not (set(e["p31"]) & wiki.NON_TOPIC_P31)
            and (topic_is_person or wiki.HUMAN not in e["p31"])]


def _in_compared_languages(entity: dict, langs: list[str], valid: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep items present in every compared language that has the topic;
    if too few remain, relax to 'at least half of them' and warn."""
    target = [l for l in langs if l in entity["sitelinks"]]
    common = [e for e in valid if all(l in e["sitelinks"] for l in target)]
    if len(common) >= RULES["basket_min_common"] or len(target) <= 1:
        return common, []
    need = max(1, -(-len(target) // 2))  # ceil(len / 2)
    common = [e for e in valid if sum(l in e["sitelinks"] for l in target) >= need]
    warning = {"code": "basket_partial",
               "text": f"Few related articles exist in all {len(target)} languages; basket uses articles present in at least {need} of them. Each language is measured on the articles it has.",
               "next": "Add or remove articles with `edit --study <id> --basket-add/--basket-remove`."}
    return common, [warning]


def _by_relevance(items: list[dict], pool: list[str], main_title: str, title_by_qid: dict[str, str]) -> list[dict]:
    """Candidate order, but items sharing a distinctive word with the topic first."""
    position = {t: i for i, t in enumerate(pool)}
    stems = _distinctive_stems(main_title, pool)

    def key(e):
        title = title_by_qid.get(e["qid"], "")
        return (0 if _stems(title) & stems else 1, position.get(title, 10 ** 6))

    return sorted(items, key=key)


def _without_hubs(items: list[dict], views: dict[str, int], main_title: str, pivot: str) -> tuple[list[dict], list[dict]]:
    """Split off generic hubs (e.g. "COVID-19" for a diet topic): they would
    dominate the basket sum and measure something else."""
    limit = RULES["basket_hub_ratio"] * max(views.get(main_title, 0), 1)
    hubs = [e for e in items if views.get(e["sitelinks"].get(pivot, ""), 0) > limit]
    return [e for e in items if e not in hubs], hubs


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


# ---------- manual edits ----------

def add_items(refs: list[str], langs: list[str], label_lang: str) -> tuple[list[dict], list[dict]]:
    """Manual additions: QIDs or lang:Title. Returns (items, warnings)."""
    warnings, qids = [], []
    for ref in refs:
        if not _is_title_ref(ref):
            qids.append(ref.upper())
            continue
        lang, title = ref.split(":", 1)
        qid = wiki.pageprops(lang, [title]).get(title, {}).get("qid")
        if qid:
            qids.append(qid)
        else:
            warnings.append({"code": "article_not_found", "text": f"Article '{title}' not found in {lang} Wikipedia.",
                             "next": "Check the exact title on Wikipedia."})
    ents = wiki.entities(qids, langs + [label_lang])
    return [item(ents[q], langs, label_lang, "added manually") for q in qids if q in ents], warnings


def matches(entry: dict, ref: str) -> bool:
    """Does a user reference (QID, label, title or lang:Title) point at this basket entry?"""
    ref_n = ref.casefold().replace("_", " ")
    if _is_title_ref(ref):
        ref_n = ref_n.split(":", 1)[1]
    return (entry["qid"].casefold() == ref_n or entry["label"].casefold() == ref_n
            or any(t.casefold() == ref_n for t in entry["titles"].values()))


def _is_title_ref(ref: str) -> bool:
    return ":" in ref and not ref.upper().startswith("Q")
