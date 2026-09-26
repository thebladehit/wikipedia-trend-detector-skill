"""CLI. Every command prints ONE compact JSON object to stdout (raw series
go to files only). Errors, including argparse errors, are JSON too:
{"status":"error","code":..,"message":..,"hint":..}"""
from __future__ import annotations

import argparse
import json
import sys

from . import study as S
from .config import SKILL_DIR, TOOL_VERSION, home
from .http import STATS, WitError

WIT = f'uv run "{SKILL_DIR}/scripts/wit.py"'


class JsonArgParser(argparse.ArgumentParser):
    def error(self, message):
        raise WitError("bad_args", message, f"See `{WIT} {self.prog.split()[-1]} --help`.")


def _split(s: str | None) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def _articles(vals: list[str] | None) -> dict:
    out = {}
    for v in vals or []:
        if ":" not in v:
            raise WitError("bad_args", f"--article expects lang:Title, got '{v}'", "Example: --article pl:\"Post (religia)\"")
        lang, title = v.split(":", 1)
        out[lang.strip().lower()] = title.strip().strip('"')
    return out


def _fill(o):
    if isinstance(o, str):
        return o.replace("uv run <skill>/scripts/wit.py", WIT)
    if isinstance(o, dict):
        return {k: _fill(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_fill(v) for v in o]
    return o


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(_fill(obj), ensure_ascii=False, indent=1, default=str) + "\n")


def cmd_run(a) -> dict:
    from .pipeline import run
    params = {"topic": a.topic, "qid": a.qid, "langs": _split(a.langs), "months": a.months, "basket": a.basket,
              "basket_size": a.basket_size, "basket_add": _split(a.basket_add), "basket_remove": _split(a.basket_remove),
              "articles": _articles(a.article), "weights": a.weights, "out": a.out, "end": a.end}
    if not a.topic and not a.qid:
        raise WitError("bad_args", "Give --topic or --qid", f'Example: {WIT} run --topic "astronomy" --langs uk')
    return run(params)


def cmd_edit(a) -> dict:
    from .pipeline import run
    st = S.load(a.study)
    p = dict(st["params"])
    before = {k: p.get(k) for k in ("langs", "months", "basket", "basket_add", "basket_remove", "weights", "articles")}
    langs = list(p["langs"])
    if a.langs:
        langs = _split(a.langs)
    langs += [l for l in _split(a.add_langs) if l not in langs]
    langs = [l for l in langs if l not in _split(a.remove_langs)]
    p["langs"] = langs
    if a.months:
        p["months"] = a.months
    if a.basket:
        p["basket"] = a.basket
    if a.basket_size:
        p["basket_size"] = a.basket_size
    p["basket_add"] = list(dict.fromkeys(p.get("basket_add", []) + _split(a.basket_add)))
    p["basket_remove"] = list(dict.fromkeys(p.get("basket_remove", []) + _split(a.basket_remove)))
    if a.weights:
        p["weights"] = a.weights
    if a.article:
        p["articles"] = {**p.get("articles", {}), **_articles(a.article)}
    if a.out:
        p["out"] = a.out
    after = {k: p.get(k) for k in before}
    res = run(p, study_id=a.study)
    if res.get("status") == "ok":
        res = {"status": "ok", "changed": {k: {"from": before[k], "to": after[k]} for k in before if before[k] != after[k]},
               **{k: v for k, v in res.items() if k != "status"}}
    return res


def cmd_report(a) -> dict:
    from . import guard, report
    d = S.latest_dir(a.study, a.version)
    analysis = json.loads((d / "analysis.json").read_text())
    compact = analysis["compact"]
    out = analysis["params"].get("texts", analysis["params"]["out"])
    compact["_out"] = out
    if a.summary is None or a.summary.strip().lower() == "auto":
        summary = report.auto_summary(compact)
        g = {"status": "ok", "problems": [], "warnings": [], "summary_source": "auto (composed from verdicts)"}
    else:
        summary = a.summary.strip()
        g = guard.check(summary, {**compact, "_directions": {l: r["direction"] for l, r in analysis["results"].items()}})
        if g["status"] == "rejected":
            return {"status": "rejected", "problems": g["problems"], "warnings": g["warnings"],
                    "allowed": g.get("allowed_numbers_hint"),
                    "next": f"Fix the summary and run report again, or use --summary auto: {WIT} report --study {a.study} --summary auto"}
    import re
    cyr = sum(bool(re.match(r"[а-яіїєґ]", ch, re.I)) for ch in summary + (a.title or ""))
    lat = sum(bool(re.match(r"[a-z]", ch, re.I)) for ch in summary + (a.title or ""))
    if (out == "en" and cyr > lat) or (out == "uk" and lat > 2 * cyr):
        g["warnings"].append(f"The report body is in '{out}' but your summary/title is in another language. "
                             f"For a consistent PDF: {WIT} edit --study {a.study} --out {'uk' if out == 'en' else 'en'} "
                             "(no new downloads), then run report again.")
    title = a.title or compact["topic"]["label"]
    path = d / "report.pdf"
    info = report.make_pdf(compact, analysis, summary, title, out, path)
    return {"status": "ok", "pdf": str(path), "guard_warnings": g["warnings"], "layout": info,
            "final_message": report.final_message(compact, summary, str(path), out),
            "note": "Send final_message to the user exactly as is and add nothing after it "
                    "(it already contains the next step)."}


def cmd_resolve(a) -> dict:
    from . import basket as B, resolve as RS, wiki
    langs = _split(a.langs)
    out = (a.out or "en").lower()
    res = RS.resolve(a.topic, langs, qid=a.qid, out=out)
    if res["status"] != "ok":
        return res
    ent = res["entity"]
    titles, missing = RS.titles_for(ent, langs)
    result = {"status": "ok", "topic": {"qid": ent["qid"], "label": wiki.label(ent, out),
                                        "description": wiki.description(ent, out), "how": res["how"]},
              "articles": titles, "missing_languages": missing}
    if a.basket and titles:
        pivot = next(iter(titles))
        items, w = B.build(ent, list(titles), pivot, out)
        result["basket"] = [{"qid": i["qid"], "label": i["label"], "reason": i["reason"]} for i in items]
    result["next"] = f"{WIT} run --qid {ent['qid']} --langs {','.join(langs)}"
    return result


def cmd_list(a) -> dict:
    return {"status": "ok", "studies": S.list_all()[: a.limit]}


def cmd_show(a) -> dict:
    d = S.latest_dir(a.study, a.version)
    compact = json.loads((d / "summary.json").read_text())
    st = S.load(a.study)
    compact["history"] = [{"version": h["version"], "at": h["at"], "langs": h["params"]["langs"],
                           "months": h["params"]["months"], "weights": h["params"].get("weights")} for h in st["history"]]
    return compact


def cmd_doctor(a) -> dict:
    import importlib
    from . import cache, http
    checks = {}
    for mod in ("numpy", "matplotlib", "fpdf", "fontTools"):
        try:
            importlib.import_module(mod)
            checks[mod] = "ok"
        except Exception as e:  # noqa: BLE001
            checks[mod] = f"missing: {e}"
    try:
        r = http.get_json("https://wikimedia.org/api/rest_v1/metrics/pageviews/aggregate/en.wikipedia/all-access/user/monthly/2024010100/2024013100")
        checks["pageviews_api"] = "ok" if r and r.get("items") else "unexpected response"
    except WitError as e:
        checks["pageviews_api"] = f"{e.code}: {e}"
    try:
        http.get_json("https://www.wikidata.org/w/api.php", {"action": "wbgetentities", "ids": "Q333", "props": "labels",
                                                             "languages": "en", "format": "json"})
        checks["wikidata_api"] = "ok"
    except WitError as e:
        checks["wikidata_api"] = f"{e.code}: {e}"
    from .config import user_agent
    ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if ok else "error", "version": TOOL_VERSION, "checks": checks, "user_agent": user_agent(),
            "data_dir": str(home()), "cache": cache.stats(),
            "hint": "" if ok else "Install uv (https://docs.astral.sh/uv/) and check internet access."}


def build_parser() -> argparse.ArgumentParser:
    p = JsonArgParser(prog="wit", description="Wikipedia interest trends across language editions.")
    sub = p.add_subparsers(dest="cmd", parser_class=JsonArgParser)

    def common_run(sp, edit=False):
        sp.add_argument("--months", type=int, help="analysis period in full months (default 24)")
        sp.add_argument("--basket", choices=["auto", "none"], help="auto: related-article basket (default); none: main article only")
        sp.add_argument("--basket-size", type=int, help="articles in basket incl. main (default 10)")
        sp.add_argument("--basket-add", help="comma list: QIDs or lang:Title")
        sp.add_argument("--basket-remove", help="comma list: QIDs, titles or labels")
        sp.add_argument("--article", action="append", help="lang:Title — use this article for a language (proxy if different item)")
        sp.add_argument("--weights", help="ranking weights, e.g. growth=0.2,size=0.3,stability=0.5")
        sp.add_argument("--out", required=not edit,
                        help="language of the user's message (uk, en, pl, ...); texts/PDF are uk or en, other languages get English texts")

    r = sub.add_parser("run", help="new analysis: resolve topic, build basket, fetch, analyse, chart")
    r.add_argument("--topic")
    r.add_argument("--qid")
    r.add_argument("--langs", required=True, help="Wikipedia language codes, e.g. uk,pl,cs")
    r.add_argument("--end", help="last month YYYY-MM (default: last complete month)")
    common_run(r)
    r.set_defaults(fn=cmd_run, months=24, basket="auto", basket_size=None)

    e = sub.add_parser("edit", help="change a saved study and recompute (new version, cached data reused)")
    e.add_argument("--study", required=True)
    e.add_argument("--langs", help="replace languages")
    e.add_argument("--add-langs")
    e.add_argument("--remove-langs")
    common_run(e, edit=True)
    e.set_defaults(fn=cmd_edit)

    rp = sub.add_parser("report", help="guard-check the summary and build a one-page PDF")
    rp.add_argument("--study", required=True)
    rp.add_argument("--summary", help="2-4 sentences using only numbers from the analysis, or 'auto'")
    rp.add_argument("--title", help="report title, e.g. the user's question")
    rp.add_argument("--version")
    rp.set_defaults(fn=cmd_report)

    rs = sub.add_parser("resolve", help="find the Wikidata item and articles without analysing")
    rs.add_argument("--topic")
    rs.add_argument("--qid")
    rs.add_argument("--langs", required=True)
    rs.add_argument("--basket", action="store_true", help="also show the candidate basket")
    rs.add_argument("--out", help="language for labels (default en)")
    rs.set_defaults(fn=cmd_resolve)

    ls = sub.add_parser("list", help="saved studies (no network)")
    ls.add_argument("--limit", type=int, default=20)
    ls.set_defaults(fn=cmd_list)

    sh = sub.add_parser("show", help="show a saved study (no network)")
    sh.add_argument("study")
    sh.add_argument("--version")
    sh.set_defaults(fn=cmd_show)

    d = sub.add_parser("doctor", help="check dependencies and API access")
    d.set_defaults(fn=cmd_doctor)
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        a = build_parser().parse_args(argv)
        if not getattr(a, "fn", None):
            raise WitError("bad_args", "No command given", f"Commands: run, edit, report, resolve, list, show, doctor. Try `{WIT} run --help`.")
        res = a.fn(a)
        if isinstance(res, dict):
            res.setdefault("api", {"requests_made": STATS["requests_made"], "cache_hits": STATS["cache_hits"]})
        _emit(res)
        return 0 if res.get("status") in ("ok", "needs_input", "rejected") else 1
    except WitError as e:
        _emit({"status": "error", "code": e.code, "message": str(e), "hint": e.hint})
        return 1
    except SystemExit as e:  # --help
        return int(e.code or 0)
    except Exception as e:  # noqa: BLE001
        _emit({"status": "error", "code": "internal", "message": f"{type(e).__name__}: {e}",
               "hint": "This is a bug in the skill. Report the command you ran."})
        return 1
