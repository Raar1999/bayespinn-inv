"""Build ``LOOP_STATE_v13.json`` from the generation-14 artefacts.

    PYTHONPATH=src python scripts/write_loop_state_g14.py

Derives from ``LOOP_STATE_v12.json`` and ``outputs/g14/mech01_pass4/``.
``new_solves = 0`` -- every number below is read from a file that already
exists, never recomputed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
PREV = ROOT / "LOOP_STATE_v12.json"
OUT = ROOT / "LOOP_STATE_v13.json"
P4 = ROOT / "outputs" / "g14" / "mech01_pass4"
VERDICT_DOC = ROOT / "docs" / "UEMPIR_MECH01_g14.md"


def read(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    st: Dict[str, Any] = read(PREV)
    pre = read(P4 / "preregister.json")
    ver = read(P4 / "verdict.json")
    res = read(P4 / "null_test.json")
    mech = read(P4 / "mechanism.json")
    cap = read(P4 / "jacobians.json")
    pilot = read(P4 / "pilot.json")

    ladder_sha = hashlib.sha256(
        (ROOT / "LADDER.md").read_bytes()).hexdigest()
    verdict_sha = hashlib.sha256(VERDICT_DOC.read_bytes()).hexdigest()

    st["generation"] = 14
    st["designation"] = "the archive is durable, and MECH-01 ends at U-EMPIR"
    st["step"] = "generation 14 complete; MECH-01 closed by verdict, not by answer"

    st["governance"].update({
        "ruling": "operator ruling of 2026-08-28, MECH-01 pass 4",
        "ladder": "LADDER.md",
        "ladder_sha256": ladder_sha,
        "ladder_edited_since_instantiation": True,
        "ladder_edit_note": (
            "one row appended to the descent/climb log, which the file itself "
            "declares append-only. The RUNGS block is byte-identical before and "
            "after -- sha256 fdc1b0e76acd95ed5442c4afec19fc8dae6ef9882caaf93ca"
            "059a89e9a208f83 -- so LD-1 is satisfied and shown rather than "
            "asserted. File hash moved a2596365... -> 184e1ef0..., exactly one "
            "line changed"),
        "rung_at_start": "L0 (under attempt)",
        "rung_at_end": "L1",
        "movement": "DESCENDED",
        "unreachability_verdicts_issued": [
            {
                "id": "U-EMPIR-MECH-01-g14",
                "class": "U-EMPIR",
                "finding": "MECH-01",
                "document": "docs/UEMPIR_MECH01_g14.md",
                "sha256": verdict_sha,
                "written_before_fallback_work": True,
                "u_0_note": (
                    "U-0 requires the verdict to precede the fallback work. It "
                    "does: the verdict document was written and hashed before "
                    "docs/G14_RESULT.md existed"),
                "expires_after_generation": 16,
                "reversible": True,
                "methods": [
                    {"n": 1, "name": "spatial localisation of the singular "
                                     "vectors (SPEC-g10-1)",
                     "generation": 10, "verdict": "FALSIFIED",
                     "mechanism": ("the vectors localise MORE as the window "
                                   "widens, the opposite of the prediction, "
                                   "tracking width at -0.433")},
                    {"n": 2, "name": "the row side -- which bias rows carry the "
                                     "trailing directions",
                     "generation": "12-13", "verdict": "FALSIFIED out of sample",
                     "mechanism": ("confounded with the split ratio b; the two "
                                   "axes do not overlap in it. corr(dz, b) "
                                   "-0.95 to -0.98, device offset spread 1.572 "
                                   "against a largest axis difference of 0.22")},
                    {"n": 3, "name": "row-subset growth against a random-row "
                                     "null, matched on row count",
                     "generation": 14, "verdict": "INCONCLUSIVE",
                     "mechanism": ("the pre-registered rule returned "
                                   "GENERIC_ROW_COUNT but its registered "
                                   "MEANING is contradicted -- all four devices "
                                   "depart from the null in the same direction, "
                                   "three at p <= 0.005. The departure is mostly "
                                   "bias spread, a smoothness property; the "
                                   "residual after spread is regressed out "
                                   "splits 0.492 against 0.947 across the two "
                                   "held-out devices, so the non-generic part "
                                   "is not reproducible")},
                ],
                "reachability_condition": (
                    "any one of: (1) a pre-registered measurement over more "
                    "than two devices, enough to say whether the surviving "
                    "residual is a property of devices or of noise; (2) a "
                    "fourth method distinct in kind -- all three so far read "
                    "the SAME Jacobians, so a design that perturbs the physics "
                    "rather than re-reading the spectrum would not share their "
                    "failure mode; (3) an instrument in which bias spread and "
                    "bias identity are independently variable, which this "
                    "repository's observation sets cannot provide"),
            }
        ],
        "why_none": None,
        "distance_to_L0": (
            "L0 is abandoned under U-EMPIR, not reached. It becomes attainable "
            "again when any of the three reachability conditions is satisfied; "
            "LD-5 obliges every future Phase A to re-evaluate them"),
    })

    st["measurements"] = {
        "PROV-08_archive_protocol": {
            "authorised_by": "operator ruling of 2026-08-28 §1 (pass 4 ruling)",
            "roles": {
                "accession": {
                    "path": "F:\\backups\\extgit-20260828",
                    "files_read_only": 854,
                    "policy": "no write command, ever. Verified after locking: "
                              "every repository still resolves its full "
                              "survivor count",
                    "not_pristine": (
                        "generation 13's ruling ordered fsck --lost-found, "
                        "which materialised .git/lost-found/ inside them. That "
                        "is the accession's state as accessioned"),
                },
                "derivative": {
                    "path": "F:\\backups\\extgit-20260828-derivative",
                    "refs_written": {"AIEF": 1, "fabkg-bench": 7,
                                     "invspec": 3, "EXT-04": 60},
                    "dangling_left": 0,
                    "note": ("the eleven refs across the three rewritten trees "
                             "pin all 536 of their dangling survivors, as the "
                             "tip analysis predicted. EXT-04's 60 are its own "
                             "separate danglers; its 1,073 mapped survivors "
                             "were already reachable"),
                },
                "bundle": {
                    "path": "F:\\backups\\extgit-20260828-bundles",
                    "carried_vs_census": {"AIEF": [63, 63],
                                          "fabkg-bench": [393, 393],
                                          "invspec": [80, 80],
                                          "EXT-04": [1073, 1073]},
                    "all_verify_okay": True,
                    "note": ("each bundle was cloned back into a fresh bare "
                             "repository and re-counted. Nothing in a bundle "
                             "can be pruned, because nothing in it is "
                             "unreachable"),
                },
            },
        },
        "MECH-01_pass_4": {
            "question": ("does widening flatten the spectrum because of WHICH "
                         "biases arrive, or merely because MORE arrive?"),
            "invocation": "PYTHONPATH=src python scripts/run_mech01_pass4.py",
            "artefact": "outputs/g14/mech01_pass4/",
            "measure_hash": pre["measure"]["measure_hash"],
            "outcomes_hash": pre["outcomes_hash"],
            "hashed_before_first_draw": True,
            "pilot": {"per_cell_s": pilot["per_cell_s"],
                      "projected_s": pilot["projected_s"],
                      "n_cells": pilot["n_cells_required"]},
            "distinct_in_kind": (
                "not a contrast. A null matched on row count by construction, "
                "which is the property pass 3 proved the spacing axis lacks"),
            "reproduction_control_R1_prime_prime": {
                "n_identical": cap["reproduction_control_R1"]["n_identical"],
                "of": cap["reproduction_control_R1"]["of"],
                "pass": cap["reproduction_control_R1"]["all_identical"]},
            "jacobians_now_stored": (
                "the thing passes 2 and 3 each had to recompute because nobody "
                "had written it down. outputs/g14/mech01_pass4/jacobians.json"),
            "null_calibration": {
                d: r["chain_null_mean_T"]
                for d, r in res["devices"].items() if r["test_ran"]},
            "per_device": {
                d: {"T": r["T"], "p_value": r["p_value"],
                    "clears_alpha": r["clears_alpha"],
                    "direction": r.get("direction")}
                for d, r in res["devices"].items() if r["test_ran"]},
            "verdict": ver["outcome"],
            "verdict_cannot_be_written_as_the_answer": (
                "GENERIC_ROW_COUNT was registered to mean 'the nested windows "
                "track the null ... nothing device-specific or regime-specific "
                "in it'. They do not track it: all four devices sit above the "
                "chain null in the same direction, three at p <= 0.005, with "
                "the nested windows consistently LESS flat than random subsets "
                "of equal size. The instrument returned a label whose "
                "registered meaning is false, and the loop may not relabel "
                "after the fact. That is inconclusive for the registered "
                "instrument, which under the ruling's §4 makes this method "
                "three"),
            "mechanism_of_the_inconclusiveness": {
                "artefact": "outputs/g14/mech01_pass4/mechanism.json",
                "is_a_test": False,
                "corr_gap_spread": {
                    d: r["mean_corr_gap_spread"]
                    for d, r in mech["devices"].items()},
                "raw_vs_residual_percentile": {
                    d: [r["mean_raw_percentile"], r["mean_residual_percentile"]]
                    for d, r in mech["devices"].items()},
                "reading": (
                    "the nested sequence is contiguous by construction and a "
                    "random subset of the same size is scattered; closely "
                    "spaced biases give nearly collinear rows, which is a "
                    "property of any smooth response. Regressing gap on the "
                    "subset's bias range, device_p10's departure vanishes "
                    "(residual percentile 0.492, exactly ordinary) while the "
                    "other three keep a residual. The two HELD-OUT devices "
                    "disagree, 0.492 against 0.947, so the non-generic part of "
                    "the departure is not reproducible"),
            },
            "defect_in_the_preregistration": (
                "the threshold clause says flattening LESS than random 'would "
                "equally refute genericity' -- which is why the test is "
                "two-sided -- while the decision rule maps everything short of "
                "IDENTITY_MATTERS onto GENERIC_ROW_COUNT. Those are "
                "inconsistent and the observed pattern fell in the gap between "
                "them. Hashed, and it stays: a pre-registration corrected after "
                "reading the result is not a pre-registration. Second such "
                "defect in two generations, after pass 3's minimum_cells "
                "justification. The pattern: hashing fixes the prose around a "
                "statistic, it does not make that prose correct"),
            "new_solves": (
                "the capture phase solves once per device because nothing "
                "stored the Jacobian; everything after is arithmetic at "
                "new_solves = 0, AST-guarded and shown non-vacuous by scanning "
                "the capture path with the same predicate"),
        },
        "DIFF-01_enactment": {
            "rule": "docs/RULES_ENACTED.md",
            "register": "docs/SWEEP_REGISTER.json",
            "guard": "tests/test_diff01_blast_radius_g14.py",
            "self_enforcing_via": (
                "a commit touching at least ten files is sweep-shaped and must "
                "appear in the register by subject. Hand edits are deep and "
                "narrow; codemods are shallow and wide"),
            "founding_entry": "the generation-13 EOL-02 sweep, 9832 lines to "
                              "fix 68, which also serves as the guard's "
                              "positive control from history",
        },
    }

    for f in st["open_findings"]:
        if f["id"] == "MECH-01":
            f["status"] = "CLOSED BY VERDICT (U-EMPIR), not by answer"
            f["note"] = (
                "three distinct methods, two falsified and one inconclusive, "
                "each with its failure mechanism measured. U-EMPIR issued at "
                "generation 14, docs/UEMPIR_MECH01_g14.md. The effect MECH-01 "
                "asks about is real and reproduces bit-for-bit; what is "
                "unreached is the mechanism. The finding is NOT withdrawn and "
                "the verdict expires after generation 16, at which point it "
                "must be re-tested or re-issued")
            f["last_tested"] = {
                "generation": 14,
                "check": ("PYTHONPATH=src python scripts/run_mech01_pass4.py; "
                          "then scripts/mech01_pass4_mechanism.py"),
                "result": ("R1'' 8 of 8 bit-identical to generation 9; verdict "
                           "GENERIC_ROW_COUNT whose registered meaning the "
                           "measurement contradicts"),
            }
        elif f["id"] == "PROV-08":
            f["status"] = "PRESERVED AND DURABLE"
            f["note"] = (
                "accession read-only at the filesystem level, derivative with "
                "rescue refs leaving zero dangling, and bundles each carrying "
                "its full census and verifying okay. The generation-13 gap -- "
                "an archive of dangling objects that a gc could still prune -- "
                "is closed without editing the accession. EXT-02 and EXT-03 "
                "remain BROKEN, MAP PRESENT in their own repositories; this "
                "loop has no authority there")
            f["last_tested"] = {
                "generation": 14,
                "check": ("git clone --bare each bundle into a fresh "
                          "repository; cat-file --batch-check over the full "
                          "old side of each commit-map; git bundle verify"),
                "result": "63/63, 393/393, 80/80, 1073/1073; all verify okay",
            }

    st["next_generation"] = {
        "blocked_on": [
            ("CI-01 / CI-02: the pull request loop/champion -> main is the "
             "operator's to open, and remains outstanding"),
        ],
        "obligations": [
            ("LD-5: re-evaluate all three of the U-EMPIR reachability "
             "conditions at Phase A, and climb if one is satisfied"),
            ("the U-EMPIR verdict expires after generation 16. It must then be "
             "re-tested or re-issued, not allowed to lapse silently"),
        ],
        "ladder": "L1, reached by descent under U-EMPIR. L3 is the floor and "
                  "is not in view.",
        "halt": None,
    }

    OUT.write_text(json.dumps(st, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    print(f"  generation       {st['generation']}")
    print(f"  rung             {st['governance']['rung_at_end']} "
          f"({st['governance']['movement']})")
    print(f"  MECH-01 verdict  {ver['outcome']}")
    print(f"  U-EMPIR sha256   {verdict_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
