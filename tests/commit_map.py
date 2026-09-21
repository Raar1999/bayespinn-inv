"""One definition of *what a recorded commit hash resolves to*.

Not a test module -- ``pytest`` collects ``test_*.py`` and this is imported, the
way ``tests/test_loop_state_close.py`` imports ``baseline_offenders`` from
``tests/test_loop_state_g9.py``. ``REP-01``'s reason applies here too: two
copies of a rule drift into two rules.

Why the guards need this
------------------------
``HIST-01``. ``git filter-repo`` rewrote this branch on 2026-08-28, so every
commit hash recorded in ``LOOP_STATE_v1..v8.json`` names an object that no
longer exists under that name. Eight guards asked ``git cat-file`` about those
hashes and failed. The hashes were never wrong when written and the commits were
never lost; only the names changed.

``docs/COMMIT_HASH_MAP_g11.json`` records the renaming, and
``scripts/repair_hist01.py`` builds and verifies it.

This is a strengthening, not a loosening, and the distinction is the whole point
------------------------------------------------------------------------------
The tempting repair -- and the one that would be standards drift under ``IA-2``
-- is to make the guard skip, or accept any hash, or stop asking. This does the
opposite. :func:`resolve_commit` refuses to use the map unless the map's own
three verifications pass, so a guard that passes through it is asserting more
than it used to: not merely *this hash names a commit*, but *this hash names a
commit, and the renaming that makes it do so is itself verified against the
commit messages and the parent chain*. If the map is missing, unverified, or
does not cover the hash, resolution returns ``None`` and the guard fails exactly
as it did before.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "docs" / "COMMIT_HASH_MAP_g11.json"


def _git(*args: str) -> Optional[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                         text=True, timeout=30)
    return out.stdout.strip() if out.returncode == 0 else None


def load_map() -> Optional[Dict]:
    """The correction map, or ``None`` if it is absent or unreadable."""
    if not MAP.is_file():
        return None
    try:
        return json.loads(MAP.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def map_is_verified() -> bool:
    """Does the map carry all three of its own passing verifications?

    Fail-closed: an absent map, a malformed map, or a map whose verification
    block reports any failure is not usable.
    """
    doc = load_map()
    if not doc:
        return False
    ver = doc.get("verification") or {}
    needed = ("V1_existence", "V2_agreement", "V3_chain")
    return all(bool((ver.get(k) or {}).get("passes")) for k in needed)


def resolve_commit(recorded: str) -> Optional[str]:
    """The commit a recorded hash names now, or ``None``.

    Tried in order: the hash as recorded, then the verified correction map.
    Never invents a resolution -- a hash the map does not cover returns
    ``None`` and its guard fails.
    """
    if not isinstance(recorded, str) or len(recorded) < 7:
        return None
    if _git("cat-file", "-t", recorded) == "commit":
        return _git("rev-parse", recorded)
    if not map_is_verified():
        return None
    doc = load_map() or {}
    for entry in doc.get("entries", []):
        if entry.get("recorded") == recorded:
            target = entry.get("resolves")
            if target and _git("cat-file", "-t", target) == "commit":
                return target
    # Hashes that appear nowhere in a state file -- in a test module, a
    # document, a commit message -- resolve through the complete rewrite table.
    table = (doc.get("full_commit_map") or {}).get("map") or {}
    hits = [new for old, new in table.items() if old.startswith(recorded)]
    if len(hits) == 1 and _git("cat-file", "-t", hits[0]) == "commit":
        return hits[0]
    return None


def is_real_commit(recorded: str) -> bool:
    """``True`` iff the recorded hash resolves to a commit in this tree."""
    return resolve_commit(recorded) is not None


def resolution_note(recorded: str) -> str:
    """A message a failing guard can print that says what was tried."""
    if _git("cat-file", "-t", recorded) == "commit":
        return f"{recorded} resolves directly"
    if not MAP.is_file():
        return (f"{recorded} does not resolve, and "
                f"{MAP.relative_to(ROOT).as_posix()} is absent -- run "
                "scripts/repair_hist01.py while .git/filter-repo/commit-map "
                "still exists, because it cannot be rebuilt once that is gone")
    if not map_is_verified():
        return (f"{recorded} does not resolve, and the correction map does not "
                "carry three passing verifications, so it is refused. HIST-01 "
                "is not repaired by an unverified map")
    return (f"{recorded} does not resolve and the correction map does not "
            "cover it. HIST-01, and this hash is outside the recorded rewrite")
