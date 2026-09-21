"""Build ``LOOP_STATE_v14.json`` — the terminal state, at ``L1``.

    PYTHONPATH=src python scripts/write_loop_state_close.py

Derives from ``LOOP_STATE_v13.json``. No generation 15 ran: the operator ruling
of 2026-08-29 closed the loop at ``L1``, and this file records the enactment of
that ruling's §2, §3 and §5 rather than a generation's measurements.

``new_solves = 0``. Every number here is read from a file that already exists or
was measured by the enactment and is cited to where it is recorded.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
PREV = ROOT / "LOOP_STATE_v13.json"
OUT = ROOT / "LOOP_STATE_v14.json"
REGISTER = ROOT / "docs" / "PREREG_REGISTER.json"


def read(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    st: Dict[str, Any] = read(PREV)

    ladder_sha = hashlib.sha256((ROOT / "LADDER.md").read_bytes()).hexdigest()
    register_sha = hashlib.sha256(REGISTER.read_bytes()).hexdigest()

    st["generation"] = 14
    st["designation"] = "closed at L1; the ruling enacted, and the loop stopped"
    st["step"] = ("the close ruling of 2026-08-29 enacted: PRE-01, the archive "
                  "accession record, and EXT-04's remote. No generation 15 ran")
    st["closed"] = True
    st["terminated"] = True

    # The ladder does not move. L1 was reached by descent at generation 14 and
    # this ruling terminates there; recording a movement would be recording one
    # that did not happen.
    st["governance"].update({
        "ruling": "operator ruling of 2026-08-29, close at L1",
        "ladder_sha256": ladder_sha,
        "rung_at_start": "L1",
        "rung_at_end": "L1",
        "movement": "HELD -- TERMINAL",
        "why_terminal": (
            "the ruling closes the loop. L0 is abandoned under the generation-14 "
            "U-EMPIR verdict, which remains reversible: LD-5 obliges any future "
            "Phase A to re-evaluate its three reachability conditions, and the "
            "verdict expires after generation 16. Terminating here is not a "
            "claim that L0 is unreachable, and LD-6 does not apply because the "
            "loop did not terminate at the L3 floor"),
    })

    st["close_enactment"] = {
        "ruling": "operator ruling of 2026-08-29",
        "enacted_on": "2026-08-29",
        "sections": {
            "S1_neither_label": {
                "status": "RATIFIED, nothing to do",
                "note": ("the refusal to write either of pass 4's registered "
                         "labels stands. outputs/g14/mech01_pass4/verdict.json "
                         "is left exactly as produced"),
            },
            "S2_accession_record": {
                "status": "ENACTED",
                "artefact": "F:/backups/extgit-20260828/README.md",
                "note": ("the archive now documents itself: census, "
                         "verification method, handling rules, and the "
                         "handling provenance the accessioning process itself "
                         "created. Pointer READMEs written beside the "
                         "derivative and the bundles"),
                "not_in_this_repository": (
                    "the README lives on F: with the archive it documents. An "
                    "accession whose only documentation is in another "
                    "repository is not documented, which is the whole reason "
                    "the ruling asked for it there"),
            },
            "S3_PRE_01": {
                "status": "ENACTED",
                "register": "docs/PREREG_REGISTER.json",
                "register_sha256": register_sha,
                "checker": "scripts/check_prereg.py",
                "guard": "tests/test_pre01_preregistration_close.py",
                "rule_text": "docs/RULES_ENACTED.md",
            },
            "S4_paper_paragraph": {
                "status": "NOT STARTED -- queued behind the operator's items",
                "note": ("the ruling assigns the pull request and EXT-05 to the "
                         "operator and the paper to this loop after them. The "
                         "MECH-01 paragraph is fixed in the ruling's §4 and is "
                         "not restated here, so there is one copy of it"),
            },
            "S5_ext04_remote": {
                "status": "ENACTED",
                "repository": "D:/FabKG_LoopLogs/s12/trackCF/clone",
                "removed": "remote 'origin' -> "
                           "D:/Fable built Fabkg Final/"
                           "fabkg-bench_snapshot_FINAL_v5/fabkg-bench",
                "method": "hand edit of .git/config, NOT git remote remove",
                "why_not_git_remote_remove": (
                    "it deletes refs/remotes/origin/* along with the remote. "
                    "Measured before the edit: 14 preserved commits are "
                    "reachable in EXT-04 only through those refs, all 14 in the "
                    "fabkg map, and 2 of the 14 resolve in no other repository "
                    "on this machine -- aff7a314 and dbab122b, both hanging off "
                    "refs/remotes/origin/sprint/GOV-D056-is6-rolling-wave-"
                    "expansion. The convenient way to perform the authorised "
                    "write would have orphaned them where they are unique"),
                "verified": {
                    "refs_before": 89, "refs_after": 89,
                    "reachable_before": 1075, "reachable_after": 1075,
                    "remotes_after": 0,
                    "sole_copy_commits_still_resolve": True,
                    "carried_by_bundle": True,
                },
                "original_config_preserved_at": (
                    "F:/backups/extgit-20260828/EXT-04/.git/config"),
            },
        },
    }

    st["open_findings"] = st["open_findings"] + [
        {
            "id": "PREREG-02",
            "severity": "MEDIUM",
            "status": "OPEN, RECORDED, NOT REPAIRABLE",
            "note": ("found by enacting PRE-01 and applying its checker to "
                     "generation 13. DOES_NOT_SEPARATE's registered meaning "
                     "carries 'the 3.1-3.5x of pass 2 was ... not a property of "
                     "the system', which its branch condition -- not both "
                     "devices clearing -- does not imply. Unlike the "
                     "generation-14 instance the loop caught, THIS ONE FIRED: "
                     "device_p10 cleared at p = 0.00062 while device_p90 did "
                     "not at p = 0.30629, so the sentence was written into "
                     "outputs/g13/mech01_pass3/verdict.json. Not repairable: "
                     "R-4 and the hashing discipline both forbid editing it"),
            "scope": ("it did not propagate. docs/UEMPIR_MECH01_g14.md rests "
                      "method 2's falsification on the measured b confound and "
                      "quotes both p-values, so the U-EMPIR verdict and the "
                      "L0 -> L1 descent are undisturbed. One meaning field in "
                      "one verdict artefact is not"),
            "forward_correction": "the sentence is not repeated in the paper",
            "last_tested": {
                "generation": "close",
                "check": "python scripts/check_prereg.py",
                "result": ("mech01-pass3-g13 DEFECTIVE as expected; 8 entailment "
                           "failures naming DOES_NOT_SEPARATE"),
            },
        },
        {
            "id": "PROV-09",
            "severity": "MEDIUM",
            "status": "OPEN, RECORDED, DELIBERATELY UNREPAIRED",
            "note": ("the generation-13 order to run git fsck --lost-found "
                     "wrote into two repositories this loop declared it had no "
                     "authority over. 13 files in "
                     "D:/Fable built Fabkg Final/.../fabkg-bench at 15:53 and 3 "
                     "in D:/p3/invspec/invspec at 22:09, both 2026-08-28. The "
                     "standing description of the EXT survey as 'read-only from "
                     "the surveyed repositories' perspective -- a copy out, no "
                     "write' is therefore not accurate for those two"),
            "why_not_repaired": (
                "deleting them would be a second write to fix the first, in "
                "repositories this loop still has no authority over. Recorded "
                "in the archive's own README instead"),
            "what_the_write_does_not_do": (
                ".git/lost-found/ is not under refs/, so it makes nothing "
                "reachable and protects nothing from gc. It is an inventory, "
                "not a rescue"),
            "last_tested": {
                "generation": "close",
                "check": "find <each repo>/.git/lost-found -type f | wc -l",
                "result": "fabkg-bench 13, invspec 3, AIEF 0, EXT-04 0",
            },
        },
    ]

    st["ruling_premises_corrected"] = st["ruling_premises_corrected"] + [
        {
            "premise": ("operator ruling of 2026-08-29 §2: --lost-found wrote "
                        "'Fifteen'"),
            "status": "NOT REPRODUCED -- the direction is right, the count is not",
            "measured": ("across the accession: AIEF 1 file, fabkg-bench 13, "
                         "invspec 3, EXT-04 65, total 82 files in 10 "
                         "directories. In the originals: fabkg-bench 13 and "
                         "invspec 3, total 16. No reading of the filesystem "
                         "gives fifteen"),
            "what_is_actually_the_case": (
                "the ruling's point stands and is larger than the number it "
                "quotes: --lost-found writes, and it wrote into two ORIGINAL "
                "repositories as well as into the accession copies. Recorded as "
                "PROV-09"),
        },
        {
            "premise": ("operator ruling of 2026-08-29 §5: check whether EXT-04 "
                        "has a remote, and if so remove it"),
            "status": "CONFIRMED, and the obvious enactment would have done harm",
            "measured": ("EXT-04 had remote 'origin' pointing at the REWRITTEN "
                         "sibling by local path. git remote remove would also "
                         "have deleted 82 refs/remotes/origin/* refs, orphaning "
                         "14 preserved commits, 2 of them the last copies"),
            "what_was_done": ("hand edit of .git/config removing only the "
                              "[remote \"origin\"] section. 89 refs and 1,075 "
                              "reachable commits before and after"),
        },
    ]

    st["operator_tasks"] = [
        ("OT-1 push and run CI -- the pull request loop/champion -> main is the "
         "operator's, per the close ruling §6, and remains outstanding. "
         "CI-01/CI-02 stay open until it runs."),
        ("OT-2 apply papers/CORRIGENDA_g6.md -- still unapplied. R-3 reserves "
         "papers/**. Nine cycles."),
        ("OT-3 preservation -- DISCHARGED for the four repositories that were "
         "copied. Accession, derivative and bundles exist, are verified against "
         "the census by mirror-clone, and the archive now documents itself. "
         "EXT-05 is reserved to the operator by the close ruling §6 and is the "
         "only preservation item left open."),
    ]

    st["next_generation"] = {
        "there_is_none": (
            "the loop is closed at L1 by the ruling of 2026-08-29. What remains "
            "is writing, not measuring"),
        "if_it_ever_resumes": [
            ("LD-5: re-evaluate all three of the U-EMPIR reachability "
             "conditions before anything else, and climb if one is satisfied"),
            ("the U-EMPIR verdict expires after generation 16. A resumption "
             "after that must re-test or re-issue it, not inherit it"),
            ("PRE-01 applies to any new pre-registration: an entry in "
             "docs/PREREG_REGISTER.json, checked by scripts/check_prereg.py, "
             "BEFORE it is hashed"),
        ],
        "blocked_on": [],
        "halt": None,
    }

    OUT.write_text(json.dumps(st, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    print(f"  closed           {st['closed']}")
    print(f"  terminated       {st['terminated']}")
    print(f"  rung             {st['governance']['rung_at_end']} "
          f"({st['governance']['movement']})")
    print(f"  open findings    {len(st['open_findings'])}")
    print(f"  register sha256  {register_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
