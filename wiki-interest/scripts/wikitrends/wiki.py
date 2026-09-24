"""Wikidata and MediaWiki Action API calls (cached for 7 days)."""
from __future__ import annotations

from .http import get_json

WD = "https://www.wikidata.org/w/api.php"
TTL = 7

DISAMBIG = "Q4167410"
HUMAN = "Q5"
LIST_ARTICLE = "Q13406463"
NON_TOPIC_P31 = {DISAMBIG, LIST_ARTICLE, "Q577", "Q3186692", "Q14795564", "Q4167836",  # year, calendar year, date, category
                 "Q13442814", "Q30612", "Q11266439"}  # scholarly article, clinical trial, template


def api(lang: str) -> str:
    return f"https://{lang}.wikipedia.org/w/api.php"


def search_entities(text: str, lang: str, limit: int = 10) -> list[dict]:
    data = get_json(WD, {"action": "wbsearchentities", "search": text, "language": lang, "uselang": lang,
                         "type": "item", "limit": limit, "format": "json"}, ttl_days=TTL)
    return data.get("search", [])


def entities(qids: list[str], langs: list[str] | None = None) -> dict[str, dict]:
    """sitelinks + labels + descriptions + P31 for up to many QIDs (batched by 50)."""
    out: dict[str, dict] = {}
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        params = {"action": "wbgetentities", "ids": "|".join(chunk), "props": "sitelinks|labels|descriptions|claims",
                  "format": "json"}
        if langs:
            params["languages"] = "|".join(dict.fromkeys(langs + ["en", "uk"]))
        data = get_json(WD, params, ttl_days=TTL)
        for q, e in data.get("entities", {}).items():
            if "missing" in e:
                continue
            p31 = [c["mainsnak"].get("datavalue", {}).get("value", {}).get("id")
                   for c in e.get("claims", {}).get("P31", [])]
            sl = {k[:-4]: v["title"] for k, v in e.get("sitelinks", {}).items()
                  if k.endswith("wiki") and k not in ("commonswiki", "specieswiki", "metawiki", "wikidatawiki",
                                                      "mediawikiwiki", "sourceswiki", "wikimaniawiki")}
            out[q] = {
                "qid": q,
                "sitelinks": sl,
                "labels": {k: v["value"] for k, v in e.get("labels", {}).items()},
                "descriptions": {k: v["value"] for k, v in e.get("descriptions", {}).items()},
                "p31": [x for x in p31 if x],
            }
    return out


def label(ent: dict, lang: str) -> str:
    return ent["labels"].get(lang) or ent["labels"].get("en") or next(iter(ent["labels"].values()), ent["qid"])


def description(ent: dict, lang: str) -> str:
    return ent["descriptions"].get(lang) or ent["descriptions"].get("en") or ""


def morelike(lang: str, title: str, limit: int = 50) -> list[str]:
    data = get_json(api(lang), {"action": "query", "list": "search", "srsearch": f"morelike:{title}",
                                "srlimit": limit, "srprop": "", "srnamespace": 0, "format": "json"}, ttl_days=TTL)
    return [x["title"] for x in data.get("query", {}).get("search", [])]


def links(lang: str, title: str, max_pages: int = 4) -> set[str]:
    out: set[str] = set()
    params = {"action": "query", "titles": title, "prop": "links", "plnamespace": 0, "pllimit": "max",
              "format": "json", "formatversion": 2}
    for _ in range(max_pages):
        data = get_json(api(lang), params, ttl_days=TTL)
        for p in data.get("query", {}).get("pages", []):
            out.update(x["title"] for x in p.get("links", []))
        if "continue" not in data:
            break
        params = {**params, **data["continue"]}
    return out


def pageprops(lang: str, titles: list[str]) -> dict[str, dict]:
    """title -> {qid, disambiguation, missing, resolved_title}; follows redirects."""
    out: dict[str, dict] = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        data = get_json(api(lang), {"action": "query", "prop": "pageprops", "ppprop": "wikibase_item|disambiguation",
                                    "titles": "|".join(chunk), "redirects": 1, "format": "json",
                                    "formatversion": 2}, ttl_days=TTL)
        q = data.get("query", {})
        back = {t: t for t in chunk}
        for n in q.get("normalized", []):
            back[n["to"]] = back.get(n["from"], n["from"])
        for r in q.get("redirects", []):
            back[r["to"]] = back.get(r["from"], r["from"])
        for p in q.get("pages", []):
            orig = back.get(p["title"], p["title"])
            pp = p.get("pageprops", {})
            out[orig] = {"title": p["title"], "missing": bool(p.get("missing") or p.get("invalid")),
                         "qid": pp.get("wikibase_item"), "disambiguation": "disambiguation" in pp}
    return out


def recent_views(lang: str, titles: list[str], days: int = 60) -> dict[str, int]:
    """Sum of last-N-day views for up to 50 titles per request (PageViewInfo)."""
    out: dict[str, int] = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        data = get_json(api(lang), {"action": "query", "prop": "pageviews", "pvipdays": days,
                                    "titles": "|".join(chunk), "format": "json", "formatversion": 2}, ttl_days=1)
        for p in data.get("query", {}).get("pages", []):
            out[p["title"]] = sum(v or 0 for v in (p.get("pageviews") or {}).values())
    return out


def redirects(lang: str, title: str) -> list[str]:
    data = get_json(api(lang), {"action": "query", "prop": "redirects", "titles": title, "rdlimit": "max",
                                "rdnamespace": 0, "format": "json", "formatversion": 2}, ttl_days=TTL)
    pages = data.get("query", {}).get("pages", [])
    return [r["title"] for r in (pages[0].get("redirects", []) if pages else [])]
