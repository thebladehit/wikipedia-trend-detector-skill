"""Study state on disk: runs/<study_id>/study.json + v1/, v2/ ... (never overwritten)."""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re

from .config import runs_dir


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")
    return s[:40] or "topic"


def study_dir(study_id: str) -> pathlib.Path:
    return runs_dir() / study_id


def exists(study_id: str) -> bool:
    return (study_dir(study_id) / "study.json").exists()


def load(study_id: str) -> dict:
    p = study_dir(study_id) / "study.json"
    if not p.exists():
        from .http import WitError
        raise WitError("unknown_study", f"No study '{study_id}'", "Run `list` to see saved studies.")
    return json.loads(p.read_text())


def new_version(study_id: str) -> tuple[str, pathlib.Path]:
    d = study_dir(study_id)
    d.mkdir(parents=True, exist_ok=True)
    n = 1 + max([int(p.name[1:]) for p in d.glob("v*") if p.name[1:].isdigit()] or [0])
    v = d / f"v{n}"
    v.mkdir()
    return f"v{n}", v


def save(study_id: str, params: dict, version: str, extra: dict) -> None:
    d = study_dir(study_id)
    prev = json.loads((d / "study.json").read_text()) if (d / "study.json").exists() else {}
    history = prev.get("history", [])
    history.append({"version": version, "at": dt.datetime.now().isoformat(timespec="seconds"),
                    "params": params, **extra})
    data = {"study": study_id, "latest": version, "params": params, "history": history}
    (d / "study.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))


def latest_dir(study_id: str, version: str | None = None) -> pathlib.Path:
    s = load(study_id)
    return study_dir(study_id) / (version or s["latest"])


def list_all() -> list[dict]:
    out = []
    for p in sorted(runs_dir().glob("*/study.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        s = json.loads(p.read_text())
        last = s["history"][-1]
        out.append({"study": s["study"], "topic": last.get("topic_label"), "langs": s["params"].get("langs"),
                    "months": s["params"].get("months"), "versions": len(s["history"]), "latest": s["latest"],
                    "updated": last["at"]})
    return out
