"""CLI. Every command prints ONE compact JSON object to stdout (raw series
go to files only). Errors, including argparse errors, are JSON too:
{"status":"error","code":..,"message":..,"hint":..}"""
from __future__ import annotations

import argparse
import json
import re
import sys

from . import study as S
from .config import TOOL_VERSION, WIT, home
from .http import STATS, WitError

# params that `edit` may change; their before/after values are reported
EDITABLE = ("langs", "months", "basket", "basket_add", "basket_remove", "weights", "articles")


# ---------- commands ----------

def cmd_run(a) -> dict:
    from .pipeline import run
    params = {"topic": a.topic, "qid": a.qid, "langs": _split(a.langs), "months": a.months, "basket": a.basket,
              "basket_size": a.basket_size, "basket_add": _split(a.basket_add), "basket_remove": _split(a.basket_remove),
              "articles": _articles(a.article), "weights": a.weights, "out": a.out, "end": a.end}
    if not a.topic and not a.qid:
        raise WitError("bad_args", "Give --topic or --qid", f'Example: {WIT} run --topic "astronomy" --langs uk')
    return run(params)


def cmd_edit(a) -> dict:
    """Apply the requested changes to a saved study and run it again as a new version."""
    from .pipeline import run
    params = dict(S.load(a.study)["params"])
    before = {k: params.get(k) for k in EDITABLE}
    _apply_edits(params, a)
    after = {k: params.get(k) for k in EDITABLE}
    res = run(params, study_id=a.study)
    if res.get("status") != "ok":
        return res
    changed = {k: {"from": before[k], "to": after[k]} for k in EDITABLE if before[k] != after[k]}
    return {"status": "ok", "changed": changed, **{k: v for k, v in res.items() if k != "status"}}


def cmd_report(a) -> dict:
    """Guard-check the agent's summary, build the PDF, return a ready final message."""
    from . import guard, report
    folder = S.latest_dir(a.study, a.version)
    analysis = json.loads((folder / "analysis.json").read_text())
    compact = analysis["compact"]
    out = analysis["params"].get("texts", analysis["params"]["out"])
    compact["_out"] = out

    if a.summary is None or a.summary.strip().lower() == "auto":
        summary = report.auto_summary(compact)
        checked = {"status": "ok", "problems": [], "warnings": [], "summary_source": "auto (composed from verdicts)"}
    else:
        summary = a.summary.strip()
        directions = {l: r["direction"] for l, r in analysis["results"].items()}
        checked = guard.check(summary, {**compact, "_directions": directions})
        if checked["status"] == "rejected":
            return {"status": "rejected", "problems": checked["problems"], "warnings": checked["warnings"],
                    "allowed": checked.get("allowed_numbers_hint"),
                    "next": f"Fix the summary and run report again, or use --summary auto: {WIT} report --study {a.study} --summary auto"}

    language_warning = _language_mismatch(summary + (a.title or ""), out, a.study)
    if language_warning:
        checked["warnings"].append(language_warning)

    path = folder / "report.pdf"
    layout = report.make_pdf(compact, analysis, summary, a.title or compact["topic"]["label"], out, path)
    return {"status": "ok", "pdf": str(path), "guard_warnings": checked["warnings"], "layout": layout,
            "final_message": report.final_message(compact, summary, str(path), out),
            "note": "Send final_message to the user exactly as is and add nothing after it "
                    "(it already contains the next step)."}


def cmd_resolve(a) -> dict:
    """Find the Wikidata item and its articles (and optionally the basket) without analysing."""
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
        items, _, _ = B.build(ent, list(titles), next(iter(titles)), out)
        result["basket"] = [{"qid": i["qid"], "label": i["label"], "reason": i["reason"]} for i in items]
    result["next"] = f"{WIT} run --qid {ent['qid']} --langs {','.join(langs)}"
    return result


def cmd_list(a) -> dict:
    return {"status": "ok", "studies": S.list_all()[: a.limit]}


def cmd_show(a) -> dict:
    compact = json.loads((S.latest_dir(a.study, a.version) / "summary.json").read_text())
    compact["history"] = [{"version": h["version"], "at": h["at"], "langs": h["params"]["langs"],
                           "months": h["params"]["months"], "weights": h["params"].get("weights")}
                          for h in S.load(a.study)["history"]]
    return compact


def cmd_doctor(a) -> dict:
    from . import cache
    from .config import user_agent
    checks = {**_check_modules(), **_check_apis()}
    ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if ok else "error", "version": TOOL_VERSION, "checks": checks, "user_agent": user_agent(),
            "data_dir": str(home()), "cache": cache.stats(),
            "hint": "" if ok else "Install uv (https://docs.astral.sh/uv/) and check internet access."}


# ---------- helpers ----------

def _apply_edits(params: dict, a) -> None:
    """Change the saved params in place according to the `edit` flags."""
    langs = _split(a.langs) if a.langs else list(params["langs"])
    langs += [l for l in _split(a.add_langs) if l not in langs]
    params["langs"] = [l for l in langs if l not in _split(a.remove_langs)]
    if a.months:
        params["months"] = a.months
    if a.basket:
        params["basket"] = a.basket
    if a.basket_size:
        params["basket_size"] = a.basket_size
    params["basket_add"] = list(dict.fromkeys(params.get("basket_add", []) + _split(a.basket_add)))
    params["basket_remove"] = list(dict.fromkeys(params.get("basket_remove", []) + _split(a.basket_remove)))
    if a.weights:
        params["weights"] = a.weights
    if a.article:
        params["articles"] = {**params.get("articles", {}), **_articles(a.article)}
    if a.out:
        params["out"] = a.out


def _language_mismatch(text: str, out: str, study: str) -> str | None:
    """Warn when the summary/title is written in another script than the report body."""
    cyrillic = sum(bool(re.match(r"[а-яіїєґ]", ch, re.I)) for ch in text)
    latin = sum(bool(re.match(r"[a-z]", ch, re.I)) for ch in text)
    if (out == "en" and cyrillic > latin) or (out == "uk" and latin > 2 * cyrillic):
        return (f"The report body is in '{out}' but your summary/title is in another language. "
                f"For a consistent PDF: {WIT} edit --study {study} --out {'uk' if out == 'en' else 'en'} "
                "(no new downloads), then run report again.")
    return None


def _check_modules() -> dict:
    import importlib
    checks = {}
    for mod in ("numpy", "matplotlib", "fpdf", "fontTools"):
        try:
            importlib.import_module(mod)
            checks[mod] = "ok"
        except Exception as e:  # noqa: BLE001
            checks[mod] = f"missing: {e}"
    return checks


def _check_apis() -> dict:
    from . import http
    checks = {}
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
    return checks


def _split(s: str | None) -> list[str]:
    """'uk, pl,,cs' -> ['uk', 'pl', 'cs']"""
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def _articles(vals: list[str] | None) -> dict:
    """['pl:Post (religia)'] -> {'pl': 'Post (religia)'}"""
    out = {}
    for v in vals or []:
        if ":" not in v:
            raise WitError("bad_args", f"--article expects lang:Title, got '{v}'", "Example: --article pl:\"Post (religia)\"")
        lang, title = v.split(":", 1)
        out[lang.strip().lower()] = title.strip().strip('"')
    return out


def _with_full_commands(o):
    """Modules write follow-up commands as `uv run <skill>/scripts/wit.py`;
    replace the placeholder with the real absolute path."""
    if isinstance(o, str):
        return o.replace("uv run <skill>/scripts/wit.py", WIT)
    if isinstance(o, dict):
        return {k: _with_full_commands(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_with_full_commands(v) for v in o]
    return o


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(_with_full_commands(obj), ensure_ascii=False, indent=1, default=str) + "\n")


# ---------- argument parsing ----------

class JsonArgParser(argparse.ArgumentParser):
    """argparse that raises WitError (printed as JSON) instead of exiting with text."""

    def error(self, message):
        raise WitError("bad_args", message, f"See `{WIT} {self.prog.split()[-1]} --help`.")


def build_parser() -> argparse.ArgumentParser:
    p = JsonArgParser(prog="wit", description="Wikipedia interest trends across language editions.")
    sub = p.add_subparsers(dest="cmd", parser_class=JsonArgParser)

    r = sub.add_parser("run", help="new analysis: resolve topic, build basket, fetch, analyse, chart")
    r.add_argument("--topic")
    r.add_argument("--qid")
    r.add_argument("--langs", required=True, help="Wikipedia language codes, e.g. uk,pl,cs")
    r.add_argument("--end", help="last month YYYY-MM (default: last complete month)")
    _add_study_options(r, edit=False)
    r.set_defaults(fn=cmd_run, months=24, basket="auto", basket_size=None)

    e = sub.add_parser("edit", help="change a saved study and recompute (new version, cached data reused)")
    e.add_argument("--study", required=True)
    e.add_argument("--langs", help="replace languages")
    e.add_argument("--add-langs")
    e.add_argument("--remove-langs")
    _add_study_options(e, edit=True)
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


def _add_study_options(sp: argparse.ArgumentParser, edit: bool) -> None:
    """Options shared by `run` and `edit`."""
    sp.add_argument("--months", type=int, help="analysis period in full months (default 24)")
    sp.add_argument("--basket", choices=["auto", "none"], help="auto: related-article basket (default); none: main article only")
    sp.add_argument("--basket-size", type=int, help="articles in basket incl. main (default 10)")
    sp.add_argument("--basket-add", help="comma list: QIDs or lang:Title")
    sp.add_argument("--basket-remove", help="comma list: QIDs, titles or labels")
    sp.add_argument("--article", action="append", help="lang:Title — use this article for a language (proxy if different item)")
    sp.add_argument("--weights", help="ranking weights, e.g. growth=0.2,size=0.3,stability=0.5")
    sp.add_argument("--out", required=not edit,
                    help="language of the user's message (uk, en, pl, ...); texts/PDF are uk or en, other languages get English texts")


# ---------- entry point ----------

def main(argv: list[str] | None = None) -> int:
    try:
        a = build_parser().parse_args(argv)
        if not getattr(a, "fn", None):
            raise WitError("bad_args", "No command given", f"Commands: run, edit, report, resolve, list, show, doctor. Try `{WIT} run --help`.")
        res = a.fn(a)
        if isinstance(res, dict) and res.get("status") == "needs_input":
            # observed on Haiku and on a free OpenRouter model: the agent picked an
            # option itself; an instruction next to the data is followed more reliably
            res["agent_instruction"] = ("STOP. Ask the user this question with these options and wait for the answer. "
                                        "Do not choose an option yourself and do not run another analysis before they reply.")
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
