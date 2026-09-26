"""Turn raw eval runs (evals/runs/*.json, git-ignored) into readable, scrubbed
Markdown transcripts that can be committed (evals/transcripts/).

Kept: user prompts, agent text, tool calls, tool results (truncated).
Dropped: system events, thinking, tool lists, session ids, local paths.

  uv run evals/export_transcripts.py 20260926-114320_plan_fixes [more run tags...]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
RUNS = HERE / "runs"
OUT = HERE / "transcripts"
MAX_RESULT = 2500

SCRUB = [
    (re.compile(r"(/private)?/var/folders/\w+/\w+/T/wit-eval-\w+"), "<sandbox>"),
    (re.compile(r"(/private)?/var/folders/\w+/\w+/T"), "<tmp>"),
    (re.compile(r"/Users/[^/\s\"']+"), "~"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<email>"),
    (re.compile(rf"\b{re.escape(Path.home().name)}\b"), "<user>"),  # OS user in `ls -l` output
]


def scrub(text: str) -> str:
    for pattern, repl in SCRUB:
        text = pattern.sub(repl, text)
    return text


def _result_text(content) -> str:
    if isinstance(content, list):
        content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    text = str(content)
    return text if len(text) <= MAX_RESULT else text[:MAX_RESULT] + f"\n… [{len(text) - MAX_RESULT} chars cut]"


def render(run: dict, prompts: list[str]) -> str:
    r = run["result"]
    failed = [k for k, ok in r["checks"].items() if not ok]
    lines = [f"# {r['case']} — run {r['run']}: {'PASS' if r['pass'] else 'FAIL'}", "",
             f"Checks failed: {', '.join(failed) or 'none'}  ",
             f"Details: `{json.dumps({k: v for k, v in r['details'].items() if v}, ensure_ascii=False)}`  ",
             f"Agent turns: {r['agent_turns']}, tokens: {r['tokens']}, time: {r['duration_s']} s", ""]
    for i, turn in enumerate(run["transcript"]):
        lines += [f"## User (turn {i + 1})", "", prompts[i] if i < len(prompts) else "", ""]
        for e in turn:
            if e.get("type") == "assistant":
                for c in e["message"]["content"]:
                    if c["type"] == "text" and c["text"].strip():
                        lines += ["### Agent", "", c["text"], ""]
                    elif c["type"] == "tool_use":
                        arg = c["input"].get("command") or json.dumps(c["input"], ensure_ascii=False)
                        lines += [f"### Tool call: {c['name']}", "", "```", arg, "```", ""]
            elif e.get("type") == "user":
                for c in e["message"]["content"]:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        lines += ["<details><summary>Tool result</summary>", "", "```",
                                  _result_text(c.get("content")), "```", "", "</details>", ""]
    return scrub("\n".join(lines))


def main() -> int:
    cases = {c["id"]: c for c in json.loads((HERE / "cases.json").read_text())}
    for tag in sys.argv[1:]:
        files = sorted(p for p in RUNS.glob(f"{tag}_*.json") if not p.name.endswith("_summary.json"))
        out_dir = OUT / tag
        out_dir.mkdir(parents=True, exist_ok=True)
        for p in files:
            run = json.loads(p.read_text())
            case = cases.get(run["result"]["case"], {})
            prompts = [t["prompt"] if isinstance(t, dict) else t for t in case.get("turns", [])]
            (out_dir / (p.stem[len(tag) + 1:] + ".md")).write_text(render(run, prompts))
        print(f"{tag}: {len(files)} transcripts -> {out_dir.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
