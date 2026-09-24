# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Turn evals/runs/*_summary.json into a markdown table.

  uv run evals/summarize.py evals/runs/<stamp>_iter2_summary.json [...more] > evals/RESULTS.md
"""
import collections
import json
import pathlib
import sys


def table(path: pathlib.Path) -> str:
    rows = json.loads(path.read_text())
    by = collections.defaultdict(list)
    for r in rows:
        by[r["case"]].append(r)
    out = [f"### {path.name}", "",
           "| case | pass | agent turns (avg) | tokens (avg) | time s (avg) | cost $ (avg) | failed checks |",
           "|---|---|---|---|---|---|---|"]
    for case, rs in by.items():
        n = len(rs)
        fails = collections.Counter(k for r in rs for k, v in r["checks"].items() if not v)
        out.append(f"| {case} | {sum(r['pass'] for r in rs)}/{n} | {sum(r['agent_turns'] for r in rs) / n:.1f} | "
                   f"{sum(r['tokens'] for r in rs) / n / 1000:.0f}k | {sum(r['duration_s'] for r in rs) / n:.0f} | "
                   f"{sum(r['cost'] for r in rs) / n:.3f} | {', '.join(f'{k}×{v}' for k, v in fails.items()) or '—'} |")
    total = len(rows)
    out.append(f"| **total** | **{sum(r['pass'] for r in rows)}/{total}** | {sum(r['agent_turns'] for r in rows) / total:.1f} | "
               f"{sum(r['tokens'] for r in rows) / total / 1000:.0f}k | {sum(r['duration_s'] for r in rows) / total:.0f} | "
               f"{sum(r['cost'] for r in rows) / total:.3f} | |")
    return "\n".join(out)


if __name__ == "__main__":
    print("\n\n".join(table(pathlib.Path(p)) for p in sys.argv[1:]))
