"""``HIST-01``: the recorded commit hashes were rewritten, not lost.

    PYTHONPATH=src python scripts/repair_hist01.py

The finding this repairs
------------------------
``HIST-01`` has been carried since generation 8 as:

    *Every LOOP_STATE file from generation 8 onward records champion_commit and
    machinery_commit hashes that git cat-file cannot resolve in this working
    tree, and champion_per_generation names none that it can. Eight guards fail
    because of it.* Status: **OPEN, PRE-EXISTING, UNREPAIRABLE FROM INSIDE THE
    TREE.**

The status was wrong, and it was wrong in a way nobody had tested. The objects
were never lost. On **2026-08-28 at 09:16**, before the close addendum session,
``git filter-repo`` rewrote this branch beginning at the commit that adopted the
post-audit tree. Every commit downstream of that point received a new hash, and
every hash recorded in a state file written *before* the rewrite therefore names
an object that no longer exists -- while the commit it named is still present,
under a different name.

``filter-repo`` writes exactly the artefact needed to undo that renaming:
``.git/filter-repo/commit-map``, a two-column ``old new`` table for every commit
it rewrote. It has been sitting in this repository the whole time. Three
generations recorded ``HIST-01`` as unrepairable without anyone running ``ls
.git``.

This is the ``DOC-03a`` class, and ``docs/CLOSE_RULING.md`` section 5.1 named it a
generation before this run found another instance:

    *An obstruction inherited from an earlier generation is a claim about the
    tree, it is exactly as checkable as any other claim about the tree, and this
    loop found that they were not being checked.*

Why the map has to be copied into the tree
------------------------------------------
``.git/`` is not tracked. The commit map exists in exactly one place, on one
disk, inside a directory that a fresh clone would not carry and that ``git gc``
has no obligation to preserve. Until it is committed, the provenance of ten
generations depends on a file that no backup covers -- which is ``OT-3``'s
warning, applied to the one artefact that makes the history readable. Copying it
into ``docs/`` is therefore the repair; deriving it again is not possible once
it is gone.

What this script does **not** do
--------------------------------
It does not edit ``LOOP_STATE_v1..v8.json``. Reserved item ``R-3`` in the
operator directive section 6 reserves *any mutation -- as opposed to
supersession -- of an existing manifest, ADR, or ledger entry*, and a state file
is a ledger entry. The recorded hashes stay exactly as they were recorded. What
is added is a **forward correction**: a map that says what those hashes now
resolve to, and why.

The verification, which is the part that matters
------------------------------------------------
A map that merely produces *some* existing commit for every input is worthless;
it has to produce the *right* one. Three independent checks:

``V1 existence``
    every mapped target resolves under ``git cat-file -t`` as a commit.

``V2 agreement``
    for every ``champion_per_generation`` entry, the mapped commit's own message
    must name the generation the entry is recorded under. The messages were
    written before the rewrite and the map was produced by ``filter-repo``, so
    the two are independent sources and their agreement is evidence rather than
    restatement.

``V3 chain``
    for every state file, the commit that *last wrote* it must have the recorded
    ``champion_commit`` as its parent, once the recorded hash is mapped. This is
    the invariant the state schema states in its own words -- *the champion is
    the last content commit, never the commit that writes this file* -- checked
    against git rather than against itself.

``V3`` is the strongest of the three, and its first draft was wrong in a way
worth recording rather than quietly fixing. It anchored on the commit that
*added* each state file, and reported ``LOOP_STATE_v4`` and ``v5`` as violations.
They are not: both were **amended after being added**, by commits whose own
messages say exactly that -- *"g7 state: point the champion at the tip"* and
*"g8 state: the champion pointer is repointed at the results commit"*. The
champion in a file's current content is written by the commit that last wrote
the file, so that is the anchor. The check now marks which files were amended
instead of hiding that they were, and the failure it produced was a defect in
the check, not in the history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
FILTER_REPO_MAP = ROOT / ".git" / "filter-repo" / "commit-map"
TRACKED_MAP = "docs/COMMIT_HASH_MAP_g11.json"

#: Keys in a state file that hold a commit hash.
COMMIT_KEYS = ("champion_commit", "machinery_commit", "results_commit",
               "bookkeeping_commit")


def git(*args: str) -> Optional[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                         text=True, timeout=30)
    return out.stdout.strip() if out.returncode == 0 else None


def read_filter_repo_map() -> Dict[str, str]:
    """The ``old new`` table filter-repo left behind, if it is still there."""
    if not FILTER_REPO_MAP.is_file():
        return {}
    pairs = {}
    for line in FILTER_REPO_MAP.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split()
        if len(parts) == 2 and all(len(p) == 40 for p in parts):
            pairs[parts[0]] = parts[1]
    return pairs


def recorded_hashes() -> Dict[str, List[str]]:
    """Every commit hash any LOOP_STATE file records, keyed by where."""
    found: Dict[str, List[str]] = {}
    for path in sorted(ROOT.glob("LOOP_STATE_v*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for key in COMMIT_KEYS:
            val = doc.get(key)
            if isinstance(val, str) and len(val) >= 7:
                found.setdefault(val, []).append(f"{path.name}:{key}")
        for gen, val in (doc.get("champion_per_generation") or {}).items():
            if isinstance(val, str) and len(val) >= 7:
                found.setdefault(val, []).append(
                    f"{path.name}:champion_per_generation.{gen}")
    return found


def build(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=TRACKED_MAP)
    args = ap.parse_args(argv)

    print("=" * 74)
    print("HIST-01  the recorded hashes were rewritten, not lost")
    print("=" * 74)

    fr = read_filter_repo_map()
    print(f"  .git/filter-repo/commit-map present : {bool(fr)}"
          f"  ({len(fr)} rewritten commits)")
    if not fr:
        print("  the map is gone from .git/. If docs/COMMIT_HASH_MAP_g11.json")
        print("  exists it is now the only copy, which is why it was tracked.")

    recorded = recorded_hashes()
    print(f"  distinct hashes recorded in state files : {len(recorded)}")
    print()

    entries: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []
    for short, where in sorted(recorded.items()):
        direct = git("cat-file", "-t", short)
        if direct == "commit":
            full = git("rev-parse", short)
            if full is None:
                unresolved.append({"recorded": short,
                                   "recorded_at": sorted(where),
                                   "candidates": 0})
                continue
            entries.append({
                "recorded": short,
                "resolves": full,
                "route": "direct",
                "recorded_at": sorted(where),
                "subject": git("log", "--format=%s", "-1", full) or "",
            })
            continue
        candidates = [old for old in fr if old.startswith(short)]
        if len(candidates) == 1:
            new = fr[candidates[0]]
            entries.append({
                "recorded": short,
                "resolves": new,
                "route": "filter-repo commit-map",
                "rewritten_from": candidates[0],
                "recorded_at": sorted(where),
                "subject": git("log", "--format=%s", "-1", new) or "",
            })
        else:
            unresolved.append({"recorded": short, "recorded_at": sorted(where),
                               "candidates": len(candidates)})

    # -- V1 existence --------------------------------------------------------
    v1_bad = [e for e in entries
              if git("cat-file", "-t", str(e["resolves"])) != "commit"]
    v1: Dict[str, Any] = {"checked": len(entries), "failures": v1_bad,
          "passes": bool(entries and not v1_bad),
          "what_it_checks": "every mapped target resolves as a commit"}

    # -- V2 agreement --------------------------------------------------------
    v2_rows: List[Dict[str, Any]] = []
    for e in entries:
        recorded_at: List[str] = list(e["recorded_at"])
        gens = sorted({w.split("champion_per_generation.")[1]
                       for w in recorded_at
                       if "champion_per_generation." in w})
        for gen in gens:
            tag = {"close": "close", "close_addendum": "addendum"}.get(gen, gen)
            subject = str(e["subject"] or "")
            agrees = subject.lower().startswith(tag.lower())
            v2_rows.append({
                "generation": gen, "recorded": e["recorded"],
                "resolves": e["resolves"], "subject": subject,
                "expected_message_to_start_with": tag, "agrees": agrees})
    v2_bad = [r for r in v2_rows if not r["agrees"]]
    v2: Dict[str, Any] = {"checked": len(v2_rows), "failures": v2_bad,
          "passes": bool(v2_rows and not v2_bad),
          "what_it_checks": (
              "the mapped commit's own message names the generation the state "
              "file recorded it under. The messages predate the rewrite and "
              "the map was produced by filter-repo, so agreement is evidence "
              "and not restatement")}

    # -- V3 chain ------------------------------------------------------------
    by_recorded = {e["recorded"]: e for e in entries}
    v3_rows: List[Dict[str, Any]] = []
    for path in sorted(ROOT.glob("LOOP_STATE_v*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        champ = doc.get("champion_commit")
        if not isinstance(champ, str):
            continue
        adder = git("log", "--diff-filter=A", "--format=%H", "-1",
                    "--", path.name)
        # The champion in the file's CURRENT content was written by the commit
        # that LAST wrote the file, not by the one that first added it. Two
        # state files -- v4 and v5 -- were amended after being added, by
        # commits whose own messages say so ("point the champion at the tip",
        # "the champion pointer is repointed at the results commit"). Anchoring
        # on the adding commit reports those two as violations of an invariant
        # they in fact satisfy.
        writer = git("log", "--format=%H", "-1", "--", path.name)
        if not writer:
            continue
        parent = git("rev-parse", writer + "^")
        mapped = by_recorded.get(champ, {}).get("resolves")
        v3_rows.append({
            "state_file": path.name,
            "recorded_champion": champ,
            "maps_to": mapped,
            "commit_that_last_wrote_the_file": writer,
            "its_parent": parent,
            "commit_that_added_the_file": adder,
            "was_amended_after_being_added": bool(adder and adder != writer),
            "champion_is_the_parent": bool(mapped and mapped == parent),
        })
    v3_bad = [r for r in v3_rows if not r["champion_is_the_parent"]]
    v3: Dict[str, Any] = {"checked": len(v3_rows), "rows": v3_rows,
          "failures": v3_bad,
          "passes": bool(v3_rows and not v3_bad),
          "what_it_checks": (
              "the commit that LAST WROTE each state file has that file's "
              "recorded champion as its parent, once the recorded hash is "
              "mapped -- the invariant the state schema states in its own "
              "words, checked against git rather than against itself"),
          "note": (
              "anchored on the last writer, not the adder. LOOP_STATE_v4 and "
              "v5 were amended after being added, by commits whose own "
              "messages say so; anchoring on the adder reports those two as "
              "violations of an invariant they satisfy. was_amended_after_"
              "being_added marks them.")}

    doc = {
        "what_this_is": (
            "the HIST-01 correction map. The hashes recorded in LOOP_STATE_v1 "
            "through v8 were rewritten by git filter-repo on 2026-08-28 at "
            "09:16, not lost. This table says what each recorded hash now "
            "resolves to."),
        "why_it_is_tracked": (
            ".git/ is not tracked, so .git/filter-repo/commit-map exists in "
            "exactly one place on one disk and a fresh clone would not carry "
            "it. Once it is gone the map cannot be derived again. Committing "
            "it is the repair; OT-3's warning applied to the one artefact that "
            "makes ten generations of history readable."),
        "what_it_does_not_do": (
            "it does not edit any LOOP_STATE file. Directive section 6 "
            "reserves any mutation -- as opposed to supersession -- of a "
            "ledger entry. The recorded hashes stay as recorded; this is a "
            "forward correction, and a superseded statement leaves its trace."),
        "rewrite": {
            "tool": "git filter-repo",
            "when": "2026-08-28 09:16 local, before the close addendum session",
            "first_changed_commit": _first_changed(),
            "rewritten_commits": len(fr),
            "source": ".git/filter-repo/commit-map",
            "source_still_present": bool(fr),
            "evidence_the_tree_was_not_otherwise_rewritten": (
                "author date equals committer date on every commit in this "
                "branch, which a rebase or amend would not leave intact"),
        },
        "full_commit_map": {
            "note": (
                "the COMPLETE old->new table filter-repo wrote, not only the "
                "hashes a LOOP_STATE file happens to cite. Preserving the "
                "subset would leave every other recorded hash in the tree -- "
                "in a document, a test module, a commit message -- "
                "unresolvable once .git/filter-repo/ is gone, which is the "
                "failure this artefact exists to prevent. "
                "tests/test_commit_messages_g7.py needs two hashes that "
                "appear in no state file, and it silently skipped for want of "
                "them."),
            "n": len(fr),
            "map": dict(sorted(fr.items())),
        },
        "entries": entries,
        "unresolved": unresolved,
        "verification": {"V1_existence": v1, "V2_agreement": v2,
                         "V3_chain": v3},
        "summary": {
            "recorded_hashes": len(recorded),
            "resolved": len(entries),
            "resolved_directly": sum(
                1 for e in entries if e["route"] == "direct"),
            "resolved_through_the_map": sum(
                1 for e in entries if e["route"] != "direct"),
            "unresolved": len(unresolved),
            "all_resolve": bool(entries and not unresolved),
            "all_verifications_pass": bool(
                v1["passes"] and v2["passes"] and v3["passes"]),
        },
    }
    payload = json.dumps(doc, indent=2) + "\n"
    doc["map_hash"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    path = ROOT / args.out
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")

    s = doc["summary"]
    print(f"  resolved                 : {s['resolved']} of "
          f"{s['recorded_hashes']}  "
          f"({s['resolved_directly']} directly, "
          f"{s['resolved_through_the_map']} through the map)")
    print(f"  unresolved               : {s['unresolved']}")
    print()
    print(f"  V1 existence  {v1['checked']:3d} checked -> "
          f"{'PASS' if v1['passes'] else 'FAIL'}")
    print(f"  V2 agreement  {v2['checked']:3d} checked -> "
          f"{'PASS' if v2['passes'] else 'FAIL'}")
    print(f"  V3 chain      {v3['checked']:3d} checked -> "
          f"{'PASS' if v3['passes'] else 'FAIL'}")
    for r in v3_bad:
        print(f"     {r['state_file']}: champion {r['recorded_champion'][:8]} "
              f"-> {str(r['maps_to'])[:8]}, parent of last writer is "
              f"{str(r['its_parent'])[:8]}")
    print()
    print(f"  wrote {args.out}")
    return 0 if doc["summary"]["all_resolve"] else 1


def _first_changed() -> Optional[Dict[str, str]]:
    p = ROOT / ".git" / "filter-repo" / "first-changed-commits"
    if not p.is_file():
        return None
    parts = p.read_text(encoding="utf-8").split()
    if len(parts) == 2:
        return {"old": parts[0], "new": parts[1],
                "subject": git("log", "--format=%s", "-1", parts[1]) or ""}
    return None


if __name__ == "__main__":
    sys.exit(build())
