"""``OPS-02``: Phase A audits the *operator's* actions on the repository.

    PYTHONPATH=src python scripts/audit_operator_actions.py

Why this exists
---------------
On 2026-08-28 the operator ran ``git filter-repo`` at 09:16 and added a remote
at 09:20. The loop noticed **neither** until generation 11 went looking, nine
hours and one generation later. In between, a whole generation ran and closed
while:

* eight guards were failing on hashes the rewrite had renamed,
* three more were silently skipping for the same reason, one of them the
  ``DOC-07`` commit-message guard,
* ``CI-01`` was carried as ``ACCEPTED-PERMANENT`` on the premise that no remote
  would ever exist, while a remote existed.

An operator action on the tree is an **unattested change to the object of
study**. This loop was built on the premise that those get detected, and they
were not. This module is the detector.

What it audits, and why each surface
------------------------------------
``remote``
    ``git remote -v``. A remote appearing changes ``CI-01``'s status by its own
    recorded reversion condition. It appeared and nothing noticed.
``config``
    ``.git/config`` mtime and the settings that change what a commit *is* --
    ``core.autocrlf``, ``core.hooksPath``, ``user.email``, ``commit.gpgsign``.
    The line-ending category has produced three incidents, and the first was a
    config default.
``hooks``
    ``.git/hooks/`` **and** ``core.hooksPath``, because a hook path set outside
    the repository is exactly the kind of change a repository-local check does
    not see. The commit-msg hook that strips attribution lives at
    ``~/.git-hooks`` and is invisible to ``ls .git/hooks``.
``filter_repo``
    ``.git/filter-repo/``. Its presence *is* the record that history was
    rewritten, and it is the only surviving trace of the pre-rewrite SHAs.
``reflog``
    head movement not attributable to the loop's own commits: resets, checkouts,
    rebases, and reflog truncation. ``filter-repo`` expires the reflog, which is
    why this repository's own history appeared to begin on the morning of the
    rewrite.

What it does **not** do
-----------------------
It does not judge whether an operator action was correct -- that is the
operator's authority, not the loop's. It records *what changed*, so that a
generation cannot run on a tree that moved under it without saying so. A
detector that editorialised would be a detector people switch off.

It also cannot see actions that leave no trace: a file edited and reverted, a
config set and unset. It reports the surfaces it can read and names that limit
rather than implying completeness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]

#: Config keys whose value changes what a commit *is*, or where hooks live.
WATCHED_CONFIG = ("core.autocrlf", "core.hooksPath", "core.filemode",
                  "user.name", "user.email", "commit.gpgsign")

#: Reflog operations that are not the loop making a commit.
NOT_A_COMMIT = ("reset", "rebase", "checkout", "merge", "cherry-pick",
                "filter-repo", "am", "revert")


def git(*args: str) -> Optional[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                         text=True, timeout=60)
    return out.stdout.strip() if out.returncode == 0 else None


def _mtime(p: Path) -> Optional[str]:
    if not p.exists():
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(p.stat().st_mtime))


def audit_remote() -> Dict[str, Any]:
    raw = git("remote", "-v") or ""
    remotes = sorted({ln.split()[0] for ln in raw.splitlines() if ln.strip()})
    urls = sorted({ln.split()[1] for ln in raw.splitlines() if len(ln.split()) > 1})
    return {
        "surface": "remote",
        "n_remotes": len(remotes),
        "remotes": remotes,
        "urls": urls,
        "present": bool(remotes),
        "why_it_matters": (
            "a remote appearing reverts CI-01 from ACCEPTED-PERMANENT to "
            "OPERATOR-BLOCKED by its own recorded condition. One appeared on "
            "2026-08-28 and no generation noticed until generation 11"),
    }


def audit_config() -> Dict[str, Any]:
    cfg = ROOT / ".git" / "config"
    return {
        "surface": "config",
        "path": ".git/config",
        "mtime": _mtime(cfg),
        "sha256": (hashlib.sha256(cfg.read_bytes()).hexdigest()
                   if cfg.is_file() else None),
        "watched": {k: git("config", "--get", k) for k in WATCHED_CONFIG},
        "why_it_matters": (
            "core.autocrlf at system level with no .gitattributes was the "
            "first of three line-ending incidents; core.hooksPath decides "
            "whether the repository's hooks are the ones that run"),
    }


def audit_hooks() -> Dict[str, Any]:
    hooks_path = git("config", "--get", "core.hooksPath")
    local = ROOT / ".git" / "hooks"
    active_dir = Path(os.path.expanduser(hooks_path)) if hooks_path else local
    installed: List[Dict[str, Any]] = []
    if active_dir.is_dir():
        for f in sorted(active_dir.iterdir()):
            if f.is_file() and not f.name.endswith(".sample"):
                installed.append({
                    "name": f.name,
                    "executable": os.access(f, os.X_OK),
                    "mtime": _mtime(f),
                    "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                })
    return {
        "surface": "hooks",
        "core_hooksPath": hooks_path,
        "hooks_directory_in_use": str(active_dir),
        "is_outside_the_repository": bool(
            hooks_path and not str(active_dir).startswith(str(ROOT))),
        "installed": installed,
        "n_installed": len(installed),
        "why_it_matters": (
            "the commit-msg hook that strips attribution trailers lives "
            "outside this repository, so `ls .git/hooks` reports nothing and a "
            "repository-local check would conclude no hook is installed"),
    }


def audit_filter_repo() -> Dict[str, Any]:
    d = ROOT / ".git" / "filter-repo"
    present = d.is_dir()
    rows: Dict[str, Any] = {
        "surface": "filter_repo",
        "present": present,
        "directory": ".git/filter-repo",
        "why_it_matters": (
            "its presence IS the record that history was rewritten. It is also "
            "the only surviving trace of the pre-rewrite SHAs: no preservation "
            "copy holds a .git, and the archive zip is the pre-loop repository"),
    }
    if present:
        rows["mtime"] = _mtime(d)
        rows["files"] = sorted(f.name for f in d.iterdir() if f.is_file())
        cmap = d / "commit-map"
        if cmap.is_file():
            lines = cmap.read_text(encoding="utf-8").splitlines()[1:]
            pairs = [ln.split() for ln in lines if len(ln.split()) == 2]
            rows["rewritten_commits"] = len(pairs)
            rows["unchanged_by_the_rewrite"] = sum(
                1 for p in pairs if p[0] == p[1])
        rows["tracked_copy"] = "docs/COMMIT_HASH_MAP_g11.json"
        rows["tracked_copy_present"] = (
            ROOT / "docs" / "COMMIT_HASH_MAP_g11.json").is_file()
    return rows


def audit_reflog() -> Dict[str, Any]:
    raw = git("reflog", "--date=iso", "--format=%h%x1f%gd%x1f%gs%x1f%cd") or ""
    entries, foreign = [], []
    for ln in raw.splitlines():
        parts = ln.split("\x1f")
        if len(parts) != 4:
            continue
        sha, ref, subject, when = parts
        row = {"sha": sha, "ref": ref, "operation": subject, "date": when}
        entries.append(row)
        head = subject.split(":", 1)[0].strip().lower()
        if any(head.startswith(op) for op in NOT_A_COMMIT):
            foreign.append(row)
    return {
        "surface": "reflog",
        "n_entries": len(entries),
        "n_not_a_commit": len(foreign),
        "not_a_commit": foreign,
        "oldest_entry": entries[-1]["date"] if entries else None,
        "why_it_matters": (
            "head movement that is not the loop committing is an operator "
            "action. filter-repo also EXPIRES the reflog, so a reflog that "
            "starts later than the repository's own first commit is itself "
            "evidence of a rewrite"),
        "reflog_is_shorter_than_the_history": _reflog_is_truncated(entries),
    }


def _reflog_is_truncated(entries: List[Dict[str, Any]]) -> Optional[bool]:
    n_commits = git("rev-list", "--count", "HEAD")
    if not n_commits:
        return None
    return len(entries) < int(n_commits)


def build() -> Dict[str, Any]:
    surfaces = [audit_remote(), audit_config(), audit_hooks(),
                audit_filter_repo(), audit_reflog()]
    doc = {
        "rule": "OPS-02",
        "what_this_is": (
            "the Phase A audit of operator actions on the repository. An "
            "operator action on the tree is an unattested change to the object "
            "of study, and this loop was built on the premise that those get "
            "detected"),
        "audited_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "head": git("rev-parse", "HEAD"),
        "surfaces": {s["surface"]: s for s in surfaces},
        "surfaces_audited": sorted(s["surface"] for s in surfaces),
        "what_it_cannot_see": (
            "actions that leave no trace -- a file edited and reverted, a "
            "config set and unset, a hook installed and removed between "
            "generations. It reports the surfaces it can read and does not "
            "imply completeness"),
        "it_does_not_judge": (
            "whether an operator action was correct is the operator's "
            "authority. This records what changed, so that a generation cannot "
            "run on a tree that moved under it without saying so"),
    }
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/g12/operator_actions.json")
    args = ap.parse_args(argv)
    doc = build()

    print("=" * 74)
    print("OPS-02  operator actions on the repository")
    print("=" * 74)
    s = doc["surfaces"]
    print(f"  remote      : {s['remote']['n_remotes']} configured "
          f"{s['remote']['urls'] or ''}")
    print(f"  config      : mtime {s['config']['mtime']}")
    for k, v in s["config"]["watched"].items():
        if v is not None:
            print(f"                {k} = {v}")
    print(f"  hooks       : {s['hooks']['n_installed']} installed in "
          f"{s['hooks']['hooks_directory_in_use']}"
          f"{'  (OUTSIDE the repository)' if s['hooks']['is_outside_the_repository'] else ''}")
    for h in s["hooks"]["installed"]:
        print(f"                {h['name']}  mtime {h['mtime']}  "
              f"executable {h['executable']}")
    fr = s["filter_repo"]
    print(f"  filter-repo : present={fr['present']}"
          + (f"  mtime {fr.get('mtime')}  "
             f"{fr.get('rewritten_commits')} commits rewritten"
             if fr["present"] else ""))
    rl = s["reflog"]
    print(f"  reflog      : {rl['n_entries']} entries, "
          f"{rl['n_not_a_commit']} not a commit, truncated="
          f"{rl['reflog_is_shorter_than_the_history']}")
    for e in rl["not_a_commit"]:
        print(f"                {e['date']}  {e['operation']}")

    p = ROOT / args.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2) + "\n",
                 encoding="utf-8", newline="\n")
    print(f"\n  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
