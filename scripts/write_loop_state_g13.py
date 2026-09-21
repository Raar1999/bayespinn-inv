"""Build ``LOOP_STATE_v12.json`` from the generation-13 artefacts.

    PYTHONPATH=src python scripts/write_loop_state_g13.py

Derives from ``LOOP_STATE_v11.json`` and the artefacts under
``outputs/g13/mech01_pass3/``. ``new_solves = 0`` -- every number below is read
from a file that already exists, never recomputed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
PREV = ROOT / "LOOP_STATE_v11.json"
OUT = ROOT / "LOOP_STATE_v12.json"
P3 = ROOT / "outputs" / "g13" / "mech01_pass3"


def read(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    st: Dict[str, Any] = read(PREV)
    pre = read(P3 / "preregister.json")
    ver = read(P3 / "verdict.json")
    ins = read(P3 / "insample.json")
    mech = read(P3 / "mechanism.json")
    held = read(P3 / "heldout.json")
    pilot = read(P3 / "pilot.json")

    st["generation"] = 13
    st["designation"] = (
        "the objects are saved, and the row side failed out of sample")
    st["step"] = "generation 13 complete"

    # ---- governance -----------------------------------------------------
    st["governance"].update({
        "ruling": ("operator ruling of 2026-08-28, PROV-08 / CI-02 / "
                   "MECH-01 pass 3"),
        "rung_at_start": "L1",
        "rung_at_end": "L1",
        "movement": "HELD",
        "unreachability_verdicts_issued": [],
        "why_none": (
            "MECH-01's row side is now FALSIFIED out of sample rather than "
            "inconclusive, so U-EMPIR stands at TWO distinct failed methods -- "
            "generation 10's column side and the row side. U-EMPIR requires "
            "k >= 3 by distinct methods. Pass 3 is the same method as pass 2 "
            "with a sharper statistic, stated so in the hashed "
            "pre-registration so it cannot be re-counted as a third later."),
        "distance_to_L0": (
            "MECH-01, unchanged as a blocker but narrowed: the row-side "
            "mechanism is closed as a characterised failure, so a third "
            "distinct method or a U-INSTR verdict naming the missing "
            "instrument is what remains."),
    })

    # ---- measurements ---------------------------------------------------
    st["measurements"] = {
        "PROV-08_rescue": {
            "invocation": ("robocopy <repo>\\.git "
                           "F:\\backups\\extgit-20260828\\<name>\\.git "
                           "/E /XJ /R:1 /W:1"),
            "artefact": "F:\\backups\\extgit-20260828\\ (off this tree)",
            "read_only_from_the_surveyed_repositories": True,
            "census_is_full_not_sampled": True,
            "per_repository": {
                "EXT-01 AIEF_Product_Development": {
                    "mapped": 63, "original": 63, "copy": 63},
                "EXT-02 fabkg-bench": {
                    "mapped": 1106, "original": 393, "copy": 393},
                "EXT-03 invspec": {
                    "mapped": 122, "original": 80, "copy": 80},
                "EXT-04 trackCF clone": {
                    "mapped": 1106, "original": 1073, "copy": 1073},
            },
            "distinct_commits_preserved": 1216,
            "fsck_errors": 0,
            "fabkg_lineage": {
                "both": 393, "ext04_only": 680, "ext02_only": 0,
                "lost_everywhere": 33,
                "reading": ("EXT-04 is a superset, not a second record. For "
                            "680 commits it is the only surviving copy on "
                            "this machine, which makes the ruling's freeze "
                            "load-bearing rather than prudent."),
            },
            "reachability": {
                "AIEF": "0 of 8 sampled survivors reachable from a branch",
                "fabkg-bench": "0 of 8",
                "invspec": "0 of 8",
                "EXT-04": ("8 of 8 -- never rewritten, so its history is "
                           "ordinary reachable history and gc does not "
                           "threaten it"),
            },
            "still_open": (
                "the three copies are byte-faithful archives OF DANGLING "
                "OBJECTS and a gc inside a copy would prune them there too. "
                "fsck --lost-found shows 1, 7 and 3 chain tips whose "
                "ancestors cover every survivor (63/63, 393/393, 80/80), so "
                "eleven refs would pin all 536. NOT done here: writing refs "
                "into an archive edits evidence this loop was told to copy. "
                "Operator's call."),
        },
        "MECH-01_pass_3": {
            "question": (
                "does the pass-2 magnitude gap, standardised against the null "
                "the split ratio induces and pre-registered with a threshold, "
                "separate the axis where the rank climbs from the axis where "
                "it does not -- at devices the row side has never seen?"),
            "invocation": "PYTHONPATH=src python scripts/run_mech01_pass3.py",
            "artefact": "outputs/g13/mech01_pass3/",
            "measure_hash": pre["measure"]["measure_hash"],
            "outcomes_hash": pre["outcomes_hash"],
            "hashed_before_held_out_data_touched": True,
            "pilot": {"per_cell_s": pilot["per_cell_s"],
                      "projected_s": pilot["projected_s"],
                      "n_cells": pilot["n_cells_required"]},
            "held_out_devices": list(held["devices"]),
            "why_out_of_sample": (
                "selected by SPEC-g9-1's percentile rule at generation 9, "
                "never given a row weight by pass 2, and the far devices at "
                "1.22 and 1.41 decades of profile distance against p50's 0.64"),
            "reproduction_control_R1_prime": {
                "n_identical": held["reproduction_control_R1"]["n_identical"],
                "of": held["reproduction_control_R1"]["of"],
                "pass": held["reproduction_control_R1"]["all_identical"],
                "why": ("the width = 0.75 window IS generation 9's "
                        "wide_0.15_0.90 window, so its singular values must "
                        "reproduce op_points.json bit for bit"),
            },
            "verdict": ver["outcome"],
            "per_device": {
                d: {"p_value": r["test"]["p_value"],
                    "clears_alpha": r["test"]["clears_alpha"],
                    "median_dz_width": r["test"]["width_median"],
                    "median_dz_spacing": r["test"]["spacing_median"]}
                for d, r in ver["devices"].items()},
            "in_sample_contrast_not_evidence": {
                d: r["test"]["p_value"] for d, r in ins["devices"].items()},
            "reading": (
                "the pre-registered rule required BOTH held-out devices to "
                "clear. device_p10 cleared at p = 0.00062 and device_p90 did "
                "not at p = 0.30629. The discovery sample clears at both "
                "(0.0019, 0.0047), which is the AH-06 shape the ruling named: "
                "strong in sample, absent out of it. Had the rule been "
                "'either device', or had only p10 been measured, this would "
                "have been reported as a confirmation."),
            "mechanism_of_the_failure": {
                "artefact": "outputs/g13/mech01_pass3/mechanism.json",
                "is_a_test": False,
                "corr_dz_b_within_device": mech["corr_dz_b"]["within_device"],
                "device_median_spread": mech["device_median_spread"],
                "largest_axis_difference_at_matched_b": 0.22,
                "reading": (
                    "dz is very nearly a function of the split ratio b -- "
                    "correlation -0.95 to -0.98 along the width axis -- and "
                    "the device-to-device offset (1.572) dwarfs any axis "
                    "difference (<= 0.22). The statistic varies with the "
                    "window and with which device it is. The axis, the thing "
                    "the hypothesis was about, is the smallest of the three."),
                "b_matched_post_hoc": {
                    "shared_b_range": mech["b_matched"]["shared_b_range"],
                    "width_exceeds_spacing_at_all_four_devices": True,
                    "why_it_does_not_rescue_the_hypothesis": (
                        "three width cells per device, margins an order of "
                        "magnitude under the device spread, and those matched "
                        "cells are the WIDEST windows where the rank has "
                        "already saturated at 4. A residual living where the "
                        "rank is not climbing is not the proposed mechanism."),
                },
            },
            "degeneracy_fix": (
                "admissible iff n_out >= 2 and n_in >= 2 -- both Beta shape "
                "parameters >= 1, so the null is non-degenerate. Derived from "
                "the null, not chosen. Excluded exactly the narrowest width "
                "cell at all four devices, plus one spacing cell at n_in = 1."),
            "new_solves": (
                "not zero for the measurement: outputs/g9 stores singular "
                "values and never U, as pass 2 recorded. The ANALYSIS is zero "
                "and AST-guarded by tests/test_mech01_pass3_g13.py, which also "
                "scans the measurement path with the same predicate to show "
                "the guard is not vacuous."),
        },
        "EOL-02_enactment": {
            "rule": "docs/RULES_ENACTED.md",
            "guard": "tests/test_eol02_line_endings_g13.py",
            "call_sites_fixed": 68,
            "files_touched": 41,
            "csv_sites_left_alone": 2,
            "incident_while_enacting": (
                "the first mechanical pass wrote every file back through "
                "Python text mode and turned 25 CRLF files into LF -- 9,832 "
                "lines changed to fix 68. Redone over bytes, asserting per "
                "file that CRLF and LF counts are unchanged. The guard went "
                "green either way; the diffstat caught it."),
            "second_incident": (
                "writing the rule's own documentation through a shell heredoc "
                "collapsed four backslash escapes and put a literal CR into a "
                "pure-LF file, failing test_line_endings_g6.py on the document "
                "describing the line-ending rule. OPS-03's shape, fourth "
                "occurrence."),
        },
    }

    # ---- open findings --------------------------------------------------
    for f in st["open_findings"]:
        if f["id"] == "MECH-01":
            f["status"] = "OPEN, two distinct methods falsified"
            f["note"] = (
                "generation 10's column side was falsified. The row side is "
                "now falsified too: pass 3 standardised the pass-2 magnitude "
                "against the Beta null the split ratio induces, "
                "pre-registered it with an exact Mann-Whitney threshold and "
                "both outcomes hashed before the held-out devices were "
                "touched, and got DOES_NOT_SEPARATE -- p10 clears at 0.00062, "
                "p90 does not at 0.30629, and the rule required both. The "
                "mechanism is measured: dz correlates with the split ratio at "
                "-0.95 to -0.98 and the device offset (1.57) dwarfs the axis "
                "difference (<= 0.22). U-EMPIR stands at TWO failed methods "
                "and needs a third distinct one, or a U-INSTR verdict naming "
                "the missing instrument.")
            f["last_tested"] = {
                "generation": 13,
                "check": ("PYTHONPATH=src python scripts/run_mech01_pass3.py; "
                          "then scripts/mech01_pass3_mechanism.py"),
                "result": ("R1' 8 of 8 singular values bit-identical to "
                           "generation 9; verdict DOES_NOT_SEPARATE against "
                           "the pre-registration"),
            }
        elif f["id"] == "PROV-08":
            f["status"] = "OBJECTS PRESERVED, repair not attempted"
            f["note"] = (
                "1,216 distinct pre-rewrite commits copied to "
                "F:\\backups\\extgit-20260828\\, fsck clean, every copy "
                "resolving what its original resolves. EXT-04 is a superset "
                "of EXT-02 and the only record of 680 commits, so the "
                "ruling's freeze is load-bearing. 33 commits are lost "
                "everywhere. EXT-02 and EXT-03 remain BROKEN, MAP PRESENT in "
                "their own repositories -- this loop has no authority there. "
                "The copies are preserved but not yet durable; see "
                "docs/AUDIT_MASTER.md PROV-08 rescue.")
            f["last_tested"] = {
                "generation": 13,
                "check": ("git cat-file --batch-check over the full old side "
                          "of each commit-map, in the original and the copy; "
                          "git fsck --no-progress --lost-found on each copy"),
                "result": ("all three MATCH original vs copy; 0 fsck errors "
                           "in all four copies"),
            }

    st["next_generation"] = {
        "blocked_on": [
            ("CI-01 / CI-02: the pull request loop/champion -> main is the "
             "operator's to open. workflow_dispatch is closed because ci.yml "
             "is not on main."),
            ("MECH-01: a THIRD distinct method, or a U-INSTR verdict naming "
             "the instrument that does not exist. Not a fourth pass at the "
             "row side."),
        ],
        "recommended": [
            ("pin the PROV-08 survivors with eleven refs, or a bare rescue "
             "repository beside the copies, to make preservation durable"),
        ],
        "ladder": "L1 held; L0 needs MECH-01 answered.",
        "halt": None,
    }

    OUT.write_text(json.dumps(st, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    print(f"  generation      {st['generation']}")
    print(f"  rung            {st['governance']['rung_at_end']} "
          f"({st['governance']['movement']})")
    print(f"  MECH-01 verdict {ver['outcome']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
