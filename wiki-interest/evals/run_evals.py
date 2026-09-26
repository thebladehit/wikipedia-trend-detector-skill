# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run eval cases through a real agent (Claude Code headless, default Haiku 4.5).

  uv run evals/run_evals.py                      # all cases, 1 run each
  uv run evals/run_evals.py --runs 3 --case astronomy-uk-trust
  uv run evals/run_evals.py --model claude-haiku-4-5

Each run: fresh sandbox project with only this skill in .claude/skills,
`claude -p` per turn (follow-up turns use --resume), stream-json transcript
saved to evals/runs/. Automatic checks:
  skill_used      the agent loaded the skill (Skill tool or read SKILL.md)
  commands        expected wit.py commands (and arguments) were run
  must_include    regexes present in the final answers
  must_not        regexes absent from the final answers
  numbers         every number in the answers appears in tool outputs
  files           expected files (e.g. report.pdf) were produced
Transcripts must still be read by hand: checks catch regressions, not quality.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(SKILL / "scripts"))
from wikitrends.guard import _nums  # noqa: E402

TOOLS = ["Skill", "Read", "Bash(uv run:*)", "Glob"]


def sandbox() -> pathlib.Path:
    d = pathlib.Path(tempfile.mkdtemp(prefix="wit-eval-"))
    (d / ".claude" / "skills").mkdir(parents=True)
    shutil.copytree(SKILL, d / ".claude" / "skills" / "wiki-interest",
                    ignore=shutil.ignore_patterns("evals", "tests", ".venv", "__pycache__", ".pytest_cache", "uv.lock"))
    return d


def run_turn(prompt: str, cwd: pathlib.Path, model: str, session: str | None, env: dict, timeout: int) -> list[dict]:
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "stream-json", "--verbose",
           "--allowedTools", *TOOLS, "--setting-sources", "project"]
    if session:
        cmd += ["--resume", session]
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    events = []
    for line in p.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    events.append({"type": "_meta", "wall_s": round(time.time() - t0, 1), "stderr": p.stderr[-2000:]})
    return events


def digest(events: list[dict]) -> dict:
    cmds, outputs, skill_used, final = [], [], False, ""
    res = {}
    for e in events:
        if e.get("type") == "assistant":
            for c in e["message"].get("content", []):
                if c.get("type") == "tool_use":
                    if c["name"] == "Skill" and "wiki-interest" in json.dumps(c["input"]):
                        skill_used = True
                    if c["name"] == "Read" and "SKILL.md" in json.dumps(c["input"]):
                        skill_used = True
                    if c["name"] == "Bash":
                        cmds.append(c["input"].get("command", ""))
        if e.get("type") == "user":
            content = e["message"].get("content", [])
            if isinstance(content, list):
                for c in content:
                    if c.get("type") == "tool_result":
                        cc = c.get("content")
                        outputs.append(cc if isinstance(cc, str) else json.dumps(cc, ensure_ascii=False))
                    if c.get("type") == "text" and "wiki-interest" in c.get("text", "") and "Base directory" in c.get("text", ""):
                        skill_used = True
        if e.get("type") == "result":
            res = e
            final = e.get("result", "") or ""
    return {"commands": cmds, "outputs": outputs, "skill_used": skill_used, "final": final,
            "session": res.get("session_id"), "cost": res.get("total_cost_usd", 0) or 0,
            "turns": res.get("num_turns", 0), "duration_s": (res.get("duration_ms", 0) or 0) / 1000,
            "tokens": sum((res.get("usage") or {}).get(k, 0) or 0 for k in
                          ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))}


def check_numbers(answer: str, outputs: list[str]) -> list[str]:
    allowed = {abs(v) for o in outputs for _, v, _ in _nums(o)} | set(range(0, 13)) | {24, 36}
    bad = []
    for s, v, pct in _nums(answer):
        if 1990 <= v <= 2100 and not pct:
            continue
        tol = 1.0 if pct else max(0.5, 0.02 * abs(v))
        if not any(abs(abs(v) - a) <= tol for a in allowed):
            bad.append(s)
    return bad


def evaluate(case: dict, digs: list[dict]) -> dict:
    answers = "\n".join(d["final"] for d in digs)
    cmds = "\n".join(c for d in digs for c in d["commands"]).replace('"', "").replace("'", "")
    outputs = [o for d in digs for o in d["outputs"]]
    checks = {}
    checks["skill_used"] = any(d["skill_used"] for d in digs) or "wit.py" in cmds
    missing_cmd = [c for c in case.get("expect_commands", []) if c not in cmds]
    missing_arg = [a for a in case.get("expect_command_args", []) if a not in cmds]
    forbidden_cmd = [c for c in case.get("forbid_commands", []) if c in cmds]
    checks["commands"] = not missing_cmd and not missing_arg and not forbidden_cmd
    miss_inc = [p for p in case.get("must_include", []) if not re.search(p, answers, re.I)]
    checks["must_include"] = not miss_inc
    neg = re.compile(r"\b(не|ні|not|no|never)\b", re.I)
    hit_exc = [p for p in case.get("must_not_include", [])
               if any(not neg.search(answers[max(0, m.start() - 40):m.start()]) for m in re.finditer(p, answers, re.I))]
    checks["must_not"] = not hit_exc
    bad_nums = check_numbers(answers, outputs)
    checks["numbers"] = not bad_nums
    files_ok = True
    for f in case.get("expect_files", []):
        files_ok &= any(f in o and '"status": "ok"' in o for o in outputs)
    checks["files"] = files_ok
    return {"pass": all(checks.values()), "checks": checks,
            "details": {"forbidden_commands": forbidden_cmd, "missing_commands": missing_cmd, "missing_args": missing_arg, "missing_include": miss_inc,
                        "forbidden_found": hit_exc, "unsupported_numbers": bad_nums[:10]}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-haiku-4-5")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--case", action="append")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    cases = json.loads((HERE / "cases.json").read_text())
    if a.case:
        cases = [c for c in cases if c["id"] in a.case]
    out_dir = HERE / "runs"
    out_dir.mkdir(exist_ok=True)
    env = dict(os.environ)
    env.setdefault("WIKI_INTEREST_HOME", str(pathlib.Path.home() / ".cache" / "wiki-interest-evals"))
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    rows = []
    for case in cases:
        for n in range(1, a.runs + 1):
            sb = sandbox()
            digs, raw, session = [], [], None
            for prompt in case["turns"]:
                ev = run_turn(prompt, sb, a.model, session, env, a.timeout)
                raw.append(ev)
                d = digest(ev)
                session = d["session"] or session
                digs.append(d)
            r = evaluate(case, digs)
            row = {"case": case["id"], "run": n, **r, "cost": sum(d["cost"] for d in digs),
                   "agent_turns": sum(d["turns"] for d in digs), "duration_s": sum(d["duration_s"] for d in digs),
                   "tokens": sum(d["tokens"] for d in digs), "commands": [c for d in digs for c in d["commands"]],
                   "answers": [d["final"] for d in digs]}
            rows.append(row)
            (out_dir / f"{stamp}{a.tag}_{case['id']}_{n}.json").write_text(
                json.dumps({"result": row, "transcript": raw}, ensure_ascii=False, indent=1))
            print(f"{case['id']:<28} run {n}: {'PASS' if r['pass'] else 'FAIL'} "
                  f"{ {k: v for k, v in r['checks'].items() if not v} or ''} "
                  f"${row['cost']:.3f} {row['agent_turns']} turns {row['duration_s']:.0f}s", flush=True)
            shutil.rmtree(sb, ignore_errors=True)
    summary = out_dir / f"{stamp}{a.tag}_summary.json"
    summary.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    passed = sum(r["pass"] for r in rows)
    print(f"\n{passed}/{len(rows)} passed · total ${sum(r['cost'] for r in rows):.2f} · summary: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
