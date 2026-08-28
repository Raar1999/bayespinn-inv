"""``SKIP-01``: every skip the suite emits, with its reason, recorded.

    PYTHONPATH=src python scripts/report_skips.py

Why this exists
---------------
``HIST-01`` made eight guards fail and **three skip**. The eight were loud. Two
of the three were ``tests/test_commit_messages_g7.py`` -- the guard that polices
``DOC-07`` -- which had stopped running over the range it was written for
because its helper turns a non-zero ``git`` exit into ``pytest.skip``. The suite
reported green for a generation while its commit-message guard was not
guarding.

A failing guard is loud. A skipping guard reports green. The second is the more
dangerous of the two, and nothing in this repository was watching for it.

What it does
------------
Runs the suite with ``-rs``, parses every skip into ``(module, line, reason)``,
and writes them to ``outputs/g12/skips.json`` beside the pass and fail counts --
which is the *"skip counts with reasons in the same line as passes"* the rule
asks for. ``tests/test_skip_register_g12.py`` then checks each against
``docs/SKIP_REGISTER.json``.

Why the report and the check are separate
-----------------------------------------
The report costs a full suite run, minutes. A guard that did that inside the
suite would either double the runtime or recurse. So the expensive part is a
script that writes an artefact, and the cheap part is a guard over the artefact
-- the same split every measurement in this repository uses.

The cost is that the artefact can go stale, and that is not hidden: it records
the commit it was taken at, and the guard reports staleness rather than
silently trusting it.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]

#: ``SKIPPED [n] path\to\module.py:line: reason``
_SKIP = re.compile(
    r"^SKIPPED\s+\[(?P<n>\d+)\]\s+(?P<path>[^:]+):(?P<line>\d+):\s*(?P<reason>.*)$")

_COUNTS = re.compile(
    r"(?:(?P<passed>\d+) passed)?"
    r"(?:[^\n]*?(?P<failed>\d+) failed)?"
    r"(?:[^\n]*?(?P<skipped>\d+) skipped)?")


def run_suite(extra: List[str]) -> str:
    cmd = [sys.executable, "-m", "pytest", "tests", "-q", "-rs",
           "-p", "no:cacheprovider", *extra]
    env_note = "PYTHONPATH=src " + " ".join(cmd)
    print(f"  running: {env_note}")
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                         env={**_env()}, timeout=3600)
    return out.stdout + out.stderr


def _env() -> Dict[str, str]:
    import os
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return env


def parse(text: str) -> Dict[str, Any]:
    skips: List[Dict[str, Any]] = []
    for line in text.splitlines():
        m = _SKIP.match(line.strip())
        if not m:
            continue
        skips.append({
            "count": int(m.group("n")),
            "module": m.group("path").replace("\\", "/").strip(),
            "line": int(m.group("line")),
            # pytest wraps long reasons; the first line is the discriminating
            # part and is what the register keys on.
            "reason": m.group("reason").strip(),
        })
    tail = [ln for ln in text.splitlines()
            if (" passed" in ln or " failed" in ln) and " in " in ln]
    summary = tail[-1] if tail else ""
    return {"skips": skips, "summary_line": summary.strip()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/g12/skips.json")
    ap.add_argument("--from-log", default=None,
                    help="parse an existing pytest -rs log instead of running")
    args, extra = ap.parse_known_args(argv)

    print("=" * 74)
    print("SKIP-01  every skip the suite emits, with its reason")
    print("=" * 74)
    t0 = time.perf_counter()
    text = (Path(args.from_log).read_text(encoding="utf-8", errors="replace")
            if args.from_log else run_suite(extra))
    parsed = parse(text)

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip())
    by_module: Dict[str, int] = {}
    for s in parsed["skips"]:
        by_module[s["module"]] = by_module.get(s["module"], 0) + s["count"]

    doc = {
        "rule": "SKIP-01",
        "what_this_is": (
            "every skip the suite emits, recorded beside the pass and fail "
            "counts. A failing guard is loud; a skipping guard reports green"),
        "invocation": "PYTHONPATH=src python -m pytest tests -q -rs",
        "summary_line": parsed["summary_line"],
        "taken_at_commit": head,
        "working_tree_dirty_when_taken": dirty,
        "n_distinct_skip_sites": len(parsed["skips"]),
        "n_skips_total": sum(s["count"] for s in parsed["skips"]),
        "skips_by_module": dict(sorted(by_module.items())),
        "skips": parsed["skips"],
        "wall_clock_s": time.perf_counter() - t0,
        "staleness": (
            "this artefact is a measurement of one tree. "
            "tests/test_skip_register_g12.py reports it as stale rather than "
            "trusting it silently if the commit has moved"),
    }
    p = ROOT / args.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2) + "\n",
                 encoding="utf-8", newline="\n")

    print(f"  {parsed['summary_line']}")
    print(f"  distinct skip sites: {doc['n_distinct_skip_sites']}   "
          f"total skips: {doc['n_skips_total']}")
    for mod, n in doc["skips_by_module"].items():
        print(f"    {n:3d}  {mod}")
    print(f"\n  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
