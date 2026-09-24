"""Topic text -> Wikidata item -> article titles per language.

Ambiguity rule (verified on real data, see references/API_NOTES.md):
keep items with >= 1 Wikipedia article; auto-pick the leader by number of
language editions when it has >= RULES.resolve_dominance x the next one;
otherwise return needs_input with options instead of guessing."""
from __future__ import annotations

import re

from . import wiki
from .config import RULES


def guess_lang(text: str) -> str:
    if re.search(r"[іїєґІЇЄҐ]", text):
        return "uk"
    if re.search(r"[а-яА-Я]", text):
        return "uk"
    if re.search(r"[ąęłńśźżĄĘŁŃŚŹŻ]", text):
        return "pl"
    if re.search(r"[ěščřžýůťďňĚŠČŘŽÝŮŤĎŇ]", text):
        return "cs"
    return "en"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().casefold().replace("_", " "))


def _usable(ent: dict) -> bool:
    return bool(ent["sitelinks"]) and not (set(ent["p31"]) & wiki.NON_TOPIC_P31)


def resolve(topic: str | None, langs: list[str], qid: str | None = None, topic_lang: str | None = None) -> dict:
    out_lang = topic_lang or (guess_lang(topic) if topic else "en")
    if qid:
        ents = wiki.entities([qid], langs + [out_lang])
        if qid not in ents:
            return {"status": "error", "code": "unknown_qid", "message": f"{qid} not found in Wikidata",
                    "hint": "Use `resolve --topic \"...\"` to find the right QID."}
        return {"status": "ok", "entity": ents[qid], "how": "qid given"}

    search_langs = list(dict.fromkeys([out_lang] + langs[:3] + ["en"]))
    hits: dict[str, dict] = {}
    for sl in search_langs:
        for h in wiki.search_entities(topic, sl):
            hits.setdefault(h["id"], h)
    if not hits:
        return {"status": "needs_input", "reason": "topic_not_found",
                "question": f"Nothing found in Wikidata for '{topic}'. Rephrase the topic (e.g. in English) or name a specific Wikipedia article.",
                "options": [],
                "next": "uv run <skill>/scripts/wit.py run --topic \"<other wording>\" --langs " + ",".join(langs)}

    t = _norm(topic)
    exact = [q for q, h in hits.items()
             if _norm(h.get("label", "")) == t or _norm(h.get("match", {}).get("text", "")) == t]
    ents = wiki.entities(list(hits), langs + [out_lang])
    pool = [q for q in (exact or list(hits)) if q in ents and _usable(ents[q])]
    if not pool and exact:
        pool = [q for q in hits if q in ents and _usable(ents[q])]
    pool.sort(key=lambda q: -len(ents[q]["sitelinks"]))
    if not pool:
        return {"status": "needs_input", "reason": "topic_not_found",
                "question": f"'{topic}' has no Wikipedia article in any language. Try a broader topic.",
                "options": [], "next": ""}

    n = [len(ents[q]["sitelinks"]) for q in pool]
    dominant = len(pool) == 1 or n[0] >= RULES["resolve_dominance"] * n[1]
    if dominant and exact:
        return {"status": "ok", "entity": ents[pool[0]], "how": f"exact match, {n[0]} language editions"}
    if dominant and not exact:
        return {"status": "ok", "entity": ents[pool[0]], "how": f"closest match (no exact title match), {n[0]} language editions",
                "interpreted": True}

    options = [{"qid": q, "label": wiki.label(ents[q], out_lang), "description": wiki.description(ents[q], out_lang),
                "wikipedias": len(ents[q]["sitelinks"])} for q in pool[:6]]
    return {"status": "needs_input", "reason": "ambiguous_topic",
            "question": f"'{topic}' can mean several things. Which one?",
            "options": options,
            "next": "uv run <skill>/scripts/wit.py run --qid <QID> --langs " + ",".join(langs)}


def titles_for(entity: dict, langs: list[str]) -> tuple[dict[str, str], list[str]]:
    """Main article title per language; languages without an article."""
    have = {l: entity["sitelinks"][l] for l in langs if l in entity["sitelinks"]}
    return have, [l for l in langs if l not in have]
