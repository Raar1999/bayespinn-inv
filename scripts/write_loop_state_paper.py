"""Build ``LOOP_STATE_v15.json`` — the paper, written after the close.

    PYTHONPATH=src python scripts/write_loop_state_paper.py

Derives from ``LOOP_STATE_v14.json``. **This is not a generation and does not
reopen the loop**: ``closed`` and ``terminated`` stay true, the ladder does not
move, and no measurement was taken. It exists because ``LOOP_STATE_v14.json``
records ``OT-2`` as unapplied and ``R-3`` as reserving ``papers/**``, and both
statements stopped being true when the close ruling of 2026-08-29 §4 assigned the
paper to the loop. A ledger left saying the false thing is worse than a ledger
with one more file in it.

The precedent is ``LOOP_STATE_v9.json``, which was written after the loop closed
at ``v8`` to record the one authorised addendum.

``new_solves = 0``. Nothing here was measured; every figure is read from an
artefact that already existed or from the guard run that accepted the prose.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
PREV = ROOT / "LOOP_STATE_v14.json"
OUT = ROOT / "LOOP_STATE_v15.json"
PAPER = ROOT / "papers" / "draft.md"


def read(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    st: Dict[str, Any] = read(PREV)

    paper_sha = hashlib.sha256(PAPER.read_bytes()).hexdigest()

    st["designation"] = "the paper, written after the close"
    st["step"] = ("papers/draft.md brought up to the spine and put on the claim "
                  "surface; COR-1 applied; OT-2 discharged. No generation ran")

    # Unchanged and stated so, rather than left to be inferred.
    st["closed"] = True
    st["terminated"] = True
    st["governance"]["movement"] = "HELD -- TERMINAL, and not re-entered"
    st["governance"]["ruling"] = ("operator ruling of 2026-08-29, close ratified; "
                                  "the paper assigned to the loop")

    st["paper"] = {
        "artefact": "papers/draft.md",
        "sha256": paper_sha,
        "authority": (
            "close ruling of 2026-08-29 §4: 'Nothing further is ordered. Mine: "
            "the pull request, and EXT-05. Yours: the paper.' That assignment is "
            "what lifted R-3 over papers/**, which had reserved it since "
            "generation 0"),
        "what_was_written": [
            ("§4.2, new -- the local rank is a property of the (device, "
             "observation set) pair. The observation set is the only one of four "
             "candidate sensitivities large at all twelve operating points "
             "tested (×1.17 end to end against ×21–×39); bias-window WIDTH sets "
             "the rank and spacing does not; the climb is the spectrum "
             "flattening, with σ₁ moving ×1.148–1.195 DOWNWARD and 95.6%–97.9% "
             "of each trailing value's motion in the shape term"),
            ("§4.2 also carries MECH-01 as an OPEN question with all three "
             "failed methods characterised, and the ruling's paragraph is "
             "reproduced as a block quote so there is exactly one copy of it"),
            ("§4.3, new -- the degeneracy is global as well as local. Witness "
             "pairs in chart G at d=4 and charts J and L at d=16; WIT-02 "
             "coverage on all three sets with every set losing members; "
             "admissibility ratio 1.000; the d=16 results written in SEARCH "
             "form, not as separations; the dimension reading, not the "
             "withdrawn chart reading; and what predicts survival stated as NOT "
             "KNOWN"),
            ("§5 -- six limitations added from the close ruling's own list, "
             "including the 0.9 V upper bound as UNVALIDATED rather than "
             "failing, and the CI matrix having never executed"),
            ("§3.2 -- charts introduced before they are used, and the "
             "inherited-obstruction sentence the close ruling asked for in the "
             "methods"),
            ("the abstract and the conclusion rewritten to match, with the open "
             "question named as open in both"),
        ],
        "cor_1": {
            "status": "APPLIED",
            "closes": ["SCI-11", "OT-2"],
            "note": ("the minimal change is the operating-point clause. The "
                     "chart, dimension, window and cutoff added at the same site "
                     "are not part of COR-1 and are recorded separately in "
                     "papers/CORRIGENDA_g6.md"),
        },
        "claim_surface": {
            "joined": ["CLAIM_SURFACE (test_claim_surface_g0)",
                       "CLAIM_SURFACE_G7, and by cascade _G9, _G10, _DOC08"],
            "parked_guard_deleted": "TestParkedPapersInstance",
            "why": ("COR-1 named the first move as its own success condition. "
                    "The second is a judgement: the rewrite gave the paper the "
                    "local rank, the observation-set result and the witness "
                    "sets, and CLAIM_SURFACE_G7's stated rule is that a document "
                    "publishing the result and absent from the list is "
                    "unguarded. Leaving the strongest statements in the one "
                    "unguarded document would invert the point of the guard"),
            "what_it_cost": (
                "four real corrections, each named by a guard rather than by a "
                "reviewer: two passages naming no chart or dimension, one rank "
                "quoted without its observation window -- in the very sentence "
                "COR-1 exists to repair -- and two bare universals over a tested "
                "set"),
        },
        "not_claimed": [
            ("no d=16 witness result is written as a separation; every one is a "
             "search that found no connecting path below the floor along a "
             "straight line, and the minimum-energy path is still not computed"),
            ("MECH-01 is not answered. The conditioning hypothesis is named as "
             "future work and explicitly not claimed"),
            ("no frequency of degeneracy is compared across charts; the three "
             "searches are existence proofs at three budgets over three priors"),
            ("no margin band for refinement survival is adopted; what predicts "
             "survival is stated as not known"),
        ],
    }

    st["operator_tasks"] = [
        ("OT-1 push and run CI -- the pull request loop/champion -> main is the "
         "operator's, per the close ruling §4, and remains outstanding. "
         "CI-01/CI-02 stay open until it runs."),
        ("OT-2 apply papers/CORRIGENDA_g6.md -- DISCHARGED 2026-08-29. The close "
         "ruling assigned the paper to the loop, which lifted R-3; COR-1 is "
         "applied and SCI-11 is closed after nine cycles."),
        ("OT-3 preservation -- DISCHARGED for the four repositories that were "
         "copied. EXT-05 is reserved to the operator by the close ruling §4 and "
         "is the only preservation item left open."),
    ]

    st["next_generation"]["there_is_none"] = (
        "the loop is closed at L1 by the ruling of 2026-08-29 and this file does "
        "not reopen it. The paper was the last assigned deliverable and it is "
        "written. What is left belongs to the operator: the pull request, and "
        "EXT-05")

    OUT.write_text(json.dumps(st, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    print(f"  closed        {st['closed']}  terminated {st['terminated']}")
    print(f"  rung          {st['governance']['rung_at_end']}")
    print(f"  paper sha256  {paper_sha}")
    print(f"  OT open       {sum('DISCHARGED' not in t for t in st['operator_tasks'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
