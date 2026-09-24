"""Topic resolution on real Wikidata responses saved in tests/fixtures (no network)."""
import json
import pathlib

from wikitrends import resolve, wiki

FX = pathlib.Path(__file__).parent / "fixtures"


def _patch(monkeypatch, search_file):
    hits = json.loads((FX / search_file).read_text())["search"]
    raw = json.loads((FX / "wd_entities_candidates.json").read_text())["entities"]

    def entities(qids, langs=None):
        out = {}
        for q in qids:
            e = raw.get(q)
            if not e:
                continue
            sl = {k[:-4]: v["title"] for k, v in e.get("sitelinks", {}).items()
                  if k.endswith("wiki") and k not in ("commonswiki", "specieswiki", "metawiki", "wikidatawiki")}
            p31 = [c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in e.get("claims", {}).get("P31", [])]
            out[q] = {"qid": q, "sitelinks": sl, "labels": {"uk": {"Q308": "Меркурій", "Q925": "ртуть"}.get(q, q)},
                      "descriptions": {}, "p31": [x for x in p31 if x]}
        return out

    monkeypatch.setattr(wiki, "search_entities", lambda text, lang, limit=10: hits)
    monkeypatch.setattr(wiki, "entities", entities)


def test_astronomy_is_picked_automatically(monkeypatch):
    _patch(monkeypatch, "wd_search_astronomy_uk.json")
    r = resolve.resolve("астрономія", ["uk"])
    assert r["status"] == "ok" and r["entity"]["qid"] == "Q333"


def test_mercury_asks_the_user(monkeypatch):
    _patch(monkeypatch, "wd_search_mercury_uk.json")
    r = resolve.resolve("Меркурій", ["uk"])
    assert r["status"] == "needs_input"
    qids = [o["qid"] for o in r["options"]]
    assert qids[:2] == ["Q308", "Q925"]
    assert "Q48397" not in qids  # disambiguation item dropped
