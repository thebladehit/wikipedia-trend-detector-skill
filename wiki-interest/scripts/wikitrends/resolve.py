"""Topic text -> Wikidata item -> article titles per language.

Ambiguity rule (verified on real data, see references/API_NOTES.md):
keep items with >= 1 Wikipedia article; auto-pick the leader by number of
language editions when it has >= RULES.resolve_dominance x the next one;
otherwise return needs_input with options instead of guessing."""
from __future__ import annotations

import re

from . import wiki
from .config import RULES


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().casefold().replace("_", " "))


def _usable(ent: dict) -> bool:
    return bool(ent["sitelinks"]) and not (set(ent["p31"]) & wiki.NON_TOPIC_P31)


def resolve(topic: str | None, langs: list[str], qid: str | None = None, out: str = "en") -> dict:
    """Wikidata search matches labels in many languages, so the topic can be
    written in any language; we search in every compared language + English."""
    if qid:
        return _by_qid(qid, langs, out)

    hits = _search(topic, langs)
    if not hits:
        return {"status": "needs_input", "reason": "topic_not_found",
                "question": f"Nothing found in Wikidata for '{topic}'.",
                "hint": "Run again with the topic's English name and tell the user you did so.",
                "options": [],
                "next": "uv run <skill>/scripts/wit.py run --topic \"<other wording>\" --langs " + ",".join(langs)}

    exact = [q for q, h in hits.items()
             if _norm(h.get("label", "")) == _norm(topic) or _norm(h.get("match", {}).get("text", "")) == _norm(topic)]
    ents = wiki.entities(list(hits), langs + [out])
    pool = _real_topics(exact or list(hits), ents)
    if not pool and exact:  # exact matches were all non-topics: fall back to every hit
        pool = _real_topics(list(hits), ents)
    if not pool:
        return {"status": "needs_input", "reason": "topic_not_found",
                "question": f"'{topic}' has no Wikipedia article in any language. Try a broader topic.",
                "options": [], "next": ""}

    editions = [len(ents[q]["sitelinks"]) for q in pool]
    dominant = len(pool) == 1 or editions[0] >= RULES["resolve_dominance"] * editions[1]
    if dominant and exact:
        return {"status": "ok", "entity": ents[pool[0]], "how": f"exact match, {editions[0]} language editions"}
    if dominant:
        return {"status": "ok", "entity": ents[pool[0]],
                "how": f"closest match (no exact title match), {editions[0]} language editions", "interpreted": True}
    return _ask(topic, pool, ents, langs, out)


def _by_qid(qid: str, langs: list[str], out: str) -> dict:
    ents = wiki.entities([qid], langs + [out])
    if qid not in ents:
        return {"status": "error", "code": "unknown_qid", "message": f"{qid} not found in Wikidata",
                "hint": "Use `resolve --topic \"...\"` to find the right QID."}
    return {"status": "ok", "entity": ents[qid], "how": "qid given"}


def _search(topic: str, langs: list[str]) -> dict[str, dict]:
    """Search hits by QID, from every compared language and English."""
    hits: dict[str, dict] = {}
    for lang in dict.fromkeys(langs + ["en"]):
        for h in wiki.search_entities(topic, lang):
            hits.setdefault(h["id"], h)
    return hits


def _real_topics(qids: list[str], ents: dict[str, dict]) -> list[str]:
    """Items with a Wikipedia article that are topics, most language editions first."""
    pool = [q for q in qids if q in ents and _usable(ents[q])]
    return sorted(pool, key=lambda q: -len(ents[q]["sitelinks"]))


def _ask(topic: str, pool: list[str], ents: dict, langs: list[str], out: str) -> dict:
    options = [{"qid": q, "label": wiki.label(ents[q], out), "description": wiki.description(ents[q], out),
                "wikipedias": len(ents[q]["sitelinks"])} for q in pool[:6]]
    return {"status": "needs_input", "reason": "ambiguous_topic",
            "question": f"'{topic}' can mean several things. Which one?",
            "options": options,
            "next": "uv run <skill>/scripts/wit.py run --qid <QID> --langs " + ",".join(langs)}


def titles_for(entity: dict, langs: list[str]) -> tuple[dict[str, str], list[str]]:
    """Main article title per language; languages without an article."""
    have = {l: entity["sitelinks"][l] for l in langs if l in entity["sitelinks"]}
    return have, [l for l in langs if l not in have]
