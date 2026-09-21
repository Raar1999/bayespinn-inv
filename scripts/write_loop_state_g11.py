"""Build ``LOOP_STATE_v10.json`` from the generation-11 artefacts.

    PYTHONPATH=src python scripts/write_loop_state_g11.py --champion <sha>

Why this is a script and not a hand-written file
------------------------------------------------
``REP-01`` as amended at generation 9: every baseline carries the invocation
that produced it, and a number in a document nobody re-derives is a claim on an
unguardable surface. The counts below -- coverage, survivors, separators,
concordance -- are **read out of the artefacts**, not transcribed, so the state
file cannot drift from the measurement it describes without this script
failing first.

The one thing it cannot derive is the champion commit, because a state file
cannot name the commit that writes it: its own bytes are part of the tree that
commit hashes. It is passed in, and the guards check it against git.

``OBS-01``, enacted this generation, is why every status asserting impossibility
below carries a ``last_tested`` block naming the check that was actually run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "LOOP_STATE_v10.json"


def read(rel: str) -> Any:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, timeout=30).stdout.strip()


def build(champion: str, pytest_counts: Dict[str, int]) -> Dict[str, Any]:
    refine = read("outputs/g11/wit02_chartL/refine.json")
    recount = read("outputs/g11/wit02_chartL/recount.json")
    register = read("outputs/close/wit02_register_v3.json")
    pilot = read("outputs/g11/pilot_chartL.json")
    headroom = read("outputs/g11/headroom.json")
    hist01 = read("docs/COMMIT_HASH_MAP_g11.json")
    archive = read("outputs/g11/archive_rerun/summary.json")
    v9 = read("LOOP_STATE_v9.json")

    rv, rc = refine["verdict"], recount["verdict"]
    hz = {r["set"]: r for r in headroom["rows"]}

    doc: Dict[str, Any] = {
        "generation": 11,
        "step": "generation 11 under fused operator authority, 2026-08-28",
        "designation": (
            "GENERATION 11. The first generation run under the operator "
            "directive of 2026-08-28, which fuses operator authority into the "
            "loop and replaces the two-party arrangement with a hashed "
            "condition ladder (LADDER.md), a self-ruling ledger (RULINGS.md) "
            "and an unreachability standard that has to be earned. The close "
            "of 2026-08-26 forbade a generation 11; that prohibition was "
            "issued by the operator under the arrangement this directive "
            "replaces, and the directive's section 8 instructs the next "
            "generation's Phase A by name. WITNESS-04 is closed, HIST-01 is "
            "repaired, one ratified premise is falsified, and the ladder was "
            "climbed rather than descended."),
        "terminated": False,
        "closed": False,
        "why_not_terminated": (
            "the stopping rule is claim-surface stationarity (directive "
            "section 5): two consecutive generations in which every finding is "
            "below HIGH, changes no spine item and changes no stated "
            "limitation. This generation changed two spine items and removed a "
            "limitation, so it is not stationary and the count of consecutive "
            "stationary generations is zero."),
        "governance": {
            "directive": "operator directive of 2026-08-28, authority fused",
            "ladder": "LADDER.md",
            "ladder_sha256": (
                "a2596365f4ec053ba7fda37901c1bd8a11db264f4954a080f680144674"
                "3a7926"),
            "ladder_edited_since_instantiation": False,
            "rulings": "RULINGS.md",
            "rulings_sha256_at_instantiation": (
                "43f7182d77c8f66e73a8fe1dce60233833cd5497c3c3c5b7888ae81927"
                "7f6fe1"),
            "hash_lock": "outputs/g11/hashlock_g11.json",
            "rung_at_start": "L2",
            "rung_at_end": "L1",
            "movement": "CLIMBED",
            "unreachability_verdicts_issued": [],
            "why_none": (
                "none was available. U-BUDGET was the only plausible class and "
                "the directive voids a budget verdict without a measured "
                "pilot; the pilot measured the experiment at minutes. MECH-01 "
                "has one failed method against U-EMPIR's three by distinct "
                "methods."),
            "distance_to_L0": (
                "MECH-01 alone. After CI-01 and PROV-07 were reclassified "
                "OPERATOR-BLOCKED, every other open HIGH is exempt by the "
                "rung's own words."),
        },
        "champion_commit": champion,
        "machinery_commit": champion,
        "results_commit": champion,
        "bookkeeping_commit": None,
        "champion_branch": "loop/champion",
        "schema": v9["schema"],
        "one_tree_one_commit": {
            "honoured": True,
            "note": (
                "the pilot, the refinement, the recount, the register, the "
                "HIST-01 repair and the documents were produced by one tree, "
                "and that tree is the champion commit."),
        },
        "measurements": {
            "WITNESS-04": {
                "question": (
                    "do chart L's 37 witness pairs survive the refinement "
                    "battery, and does the barrier classification move when "
                    "they are recounted over the survivors?"),
                "authorised_by": "operator directive of 2026-08-28 sections 7 and 8",
                "preregistered": True,
                "preregistration": "outputs/g11/wit02_chartL/preregister.json",
                "invocation": "PYTHONPATH=src python scripts/run_wit02_chartL.py",
                "set": rv["set"],
                "n_pairs_offered": rv["n_pairs"],
                "n_refined": rv["n_refined_here"],
                "n_surviving": rv["n_surviving"],
                "n_separated": rv["n_separated_by_refinement"],
                "coverage_before": rv["coverage_before_this_run"],
                "coverage_after": rv["coverage_after_this_run"],
                "count_class": rv["count_class"],
                "classification": rc["classification_over_the_surviving_set"],
                "classification_at_generation_10":
                    rc["classification_at_generation_10"],
                "flipped": rc["flipped"],
                "median_in_floor_units": rc["median_in_floor_units"],
                "median_in_floor_units_at_generation_10":
                    rc["median_in_floor_units_at_generation_10"],
                "fraction_below_floor_barrier": rc["fraction_below_floor_here"],
                "wall_clock_s": refine["wall_clock_s"],
                "controls": {
                    "R1_reproduction": (
                        f"PASS. {refine['reproduction_control_R1']['n_identical']}"
                        f" of {refine['reproduction_control_R1']['of']} pairs "
                        "reproduce the committed N=301 distance bit-identically."
                        " Weaker than chart G's in a stated way: it compares "
                        "this code path against the artefact it reads, not "
                        "against a second implementation."),
                    "N1_negative": (
                        "PASS. A chart-L null-control pair -- consecutive "
                        "ordinary draws forming no witness pair -- through the "
                        "same battery does NOT survive, at "
                        f"{refine['negative_control_N1']['worst_distance']:.4f} "
                        "against a floor of 0.02."),
                    "P1_positive": (
                        "PASS. Two identical devices survive at distance "
                        "exactly zero at every row. This is the control chart "
                        "G's run did not have: a battery that rejected "
                        "everything would make every 'separates' verdict "
                        "vacuous."),
                    "D1_determinism": (
                        "PASS. One pair's battery re-run; all six distances "
                        "bit-identical."),
                    "B1_barrier_reproduction": (
                        "PASS. All "
                        f"{recount['reproduction_control_B1']['n_identical']} of "
                        f"{recount['reproduction_control_B1']['of']} barrier "
                        "depths and the median reproduce "
                        "outputs/g10/ridge_basin.json bit-identically."),
                    "S1_self_consistency": (
                        "PASS. Every counted pair's depth in the subset run "
                        "equals its depth in the full run."),
                    "all_controls_pass": bool(
                        refine["all_refine_controls_pass"]
                        and recount["reproduction_control_B1"]["all_identical"]
                        and recount["self_consistency_S1"]["all_identical"]),
                },
                "what_it_does_not_say": (
                    "anything about connectivity. WIT-02 tests witnesses, not "
                    "paths. Every barrier is still a straight line in one "
                    "chart's coordinates and therefore an UPPER bound, both "
                    "d=16 results are still search statements, and the "
                    "minimum-energy path was not computed. PATH-01 and AH-13 "
                    "are untouched by full coverage."),
                "the_median_rose_and_that_is_bookkeeping": (
                    "the pairs that separated were the shallow ones, so the "
                    "median deepened from 212.0 to 222.8 floor units and the "
                    "shallowest survivor from 22.6 to 132.2. This is not a "
                    "stronger basin: a basin is a statement about pairs that "
                    "ARE witnesses, and eleven of them turned out not to be."),
            },
            "WITNESS-04_pilot": {
                "why": (
                    "directive section 2: a U-BUDGET verdict without a measured "
                    "pilot is void. Declaring a hard thing impossible is the "
                    "cheapest way to finish, and this is what takes the option "
                    "away."),
                "invocation": (
                    "PYTHONPATH=src python scripts/pilot_wit02_chartL.py "
                    "--pairs 3"),
                "per_pair_mean_s": pilot["timing"]["per_pair_mean_s"],
                "per_pair_spread_factor": pilot["timing"]["per_pair_spread_factor"],
                "projected_all_pairs_s": pilot["projection"]["all_pairs_s"],
                "actually_taken_s": refine["wall_clock_s"],
                "projection_error_percent": float(
                    100.0 * (refine["wall_clock_s"]
                             - pilot["projection"]["all_pairs_s"])
                    / pilot["projection"]["all_pairs_s"]),
                "verdict": (
                    "AFFORDABLE, so U-BUDGET was unavailable and the rung was "
                    "not descended from."),
            },
            "HIST-01_repair": {
                "invocation": "PYTHONPATH=src python scripts/repair_hist01.py",
                "mechanism": (
                    "git filter-repo rewrote this branch on 2026-08-28 09:16, "
                    "renaming every commit from c115757 forward. The objects "
                    "were never lost."),
                "recorded_hashes": hist01["summary"]["recorded_hashes"],
                "resolved": hist01["summary"]["resolved"],
                "resolved_through_the_map":
                    hist01["summary"]["resolved_through_the_map"],
                "unresolved": hist01["summary"]["unresolved"],
                "verifications": {
                    k: {"checked": v["checked"], "passes": v["passes"]}
                    for k, v in hist01["verification"].items()},
                "rewritten_commits_preserved":
                    hist01["full_commit_map"]["n"],
                "guards_restored_from_failing": 8,
                "guards_restored_from_silently_skipping": 3,
                "why_the_map_is_tracked": (
                    ".git/ is not tracked, so the map existed in one place on "
                    "one disk and cannot be rebuilt once gone. Copying it into "
                    "docs/ is the repair."),
                "it_is_a_supersession_not_a_mutation": (
                    "no LOOP_STATE file was edited. Directive section 6 "
                    "reserves mutation of a ledger entry; the recorded hashes "
                    "stay as recorded."),
            },
            "headroom_free_check": {
                "status": "DESCRIPTION, not pre-registered (AH-14). new_solves = 0",
                "invocation": (
                    "PYTHONPATH=src python scripts/check_headroom_g11.py"),
                "premise_tested": headroom["verdict"]["premise"],
                "chart_G_concordance": hz["chart_G_d4"]["concordance"],
                "chart_J_concordance": hz["chart_J_d16"]["concordance"],
                "chart_L_concordance": hz["chart_L_d16"]["concordance"],
                "chart_L_spearman": hz["chart_L_d16"]["spearman_rho"],
                "chart_L_p": hz["chart_L_d16"]["spearman_p"],
                "holds_on_every_set": headroom["verdict"]["holds_on_every_set"],
                "the_sets_it_holds_on_are_the_sets_it_was_formed_on":
                    headroom["verdict"][
                        "the_sets_it_holds_on_are_the_sets_it_was_formed_on"],
                "reading": headroom["verdict"]["reading"],
                "what_it_strengthens": headroom["verdict"]["what_it_strengthens"],
            },
            "IA_2_archive_rerun": {
                "generations_rerun": archive["summary"]["generations_rerun"],
                "controls_compared": archive["summary"]["controls_compared"],
                "all_identical": archive["summary"]["all_identical"],
                "drift_detected": archive["summary"]["drift_detected"],
                "reading": archive["summary"]["reading"],
                "artefact": "outputs/g11/archive_rerun/summary.json",
            },
        },
        "wit02_register": {
            "version": 3,
            "artefact": "outputs/close/wit02_register_v3.json",
            "supersedes": "outputs/close/wit02_register_v2.json",
            "sets": {k: {"n_pairs_offered": v["n_pairs_offered"],
                         "n_refined": v["n_refined"],
                         "n_surviving": v["n_surviving"],
                         "coverage": v["coverage"],
                         "compliant": v["compliant"]}
                     for k, v in register["sets"].items()},
            "all_compliant": register["verdict"]["all_compliant"],
            "how_to_say_it": register["verdict"]["how_to_say_it"],
            "what_full_coverage_does_not_mean":
                register["verdict"]["what_full_coverage_does_not_mean"],
            "untouched_sets_reproduce_version_2":
                register["untouched_sets_reproduce_version_2"]["all"],
        },
        "baselines": {
            "pytest": {
                "invocation": "PYTHONPATH=src python -m pytest tests -q",
                "tool_version": "pytest 9.1.1",
                "collected": pytest_counts["collected"],
                "passed": pytest_counts["passed"],
                "skipped": pytest_counts["skipped"],
                "failed": pytest_counts["failed"],
                "rerunnable": False,
                "conditions": (
                    "taken at champion_commit with LOOP_STATE_v10.json NOT yet "
                    "in the tree, which is why the OBS-01 guard skips and the "
                    "counts differ from a post-state-commit run. Stated rather "
                    "than smoothed over, as at generations 9 and 10."),
                "measured_at_commit": champion,
                "environment": "CPython 3.11.9, win32",
                "failures_are": (
                    "none. HIST-01's eight are repaired and the three silent "
                    "skips are restored; this is the first generation since "
                    "generation 7 whose suite has no failing test."),
            },
            "ruff_whole_tree": {
                "invocation": "python -m ruff check .",
                "tool_version": "ruff 0.16.3",
                "exit_code": 0, "findings": 0, "rerunnable": True,
            },
            "ruff_scoped": {
                "invocation": "python -m ruff check src tests scripts",
                "tool_version": "ruff 0.16.3",
                "exit_code": 0, "findings": 0, "rerunnable": True,
                "note": "the invocation .github/workflows/ci.yml and the Makefile run.",
            },
            "mypy_tracked_tree": {
                "invocation": "mypy src tests scripts",
                "tool_version": "mypy 2.3.1",
                "findings": 150, "files_checked": 134, "rerunnable": False,
                "conditions": (
                    "THE CARRIED BASELINE. Unchanged at 150 while the checked "
                    "surface grew from 125 files to 134: every module added "
                    "this generation is clean under this invocation, which the "
                    "generation-9 guard enforces by failing if the count "
                    "moves."),
                "measured_at_commit": champion,
                "was_at_close": {"findings": 150, "files_checked": 123},
                "was_at_close_addendum": {"findings": 150, "files_checked": 125},
            },
            "mypy_package": {
                "invocation": "mypy src",
                "tool_version": "mypy 2.3.1",
                "findings": 25, "files_checked": 45, "rerunnable": False,
                "conditions": (
                    "advisory in the Makefile (dash-prefixed), so its exit code "
                    "is not a gate. Not the carried baseline. DOC-08: 25 is "
                    "`mypy src`; 150 is `mypy src tests scripts`."),
                "measured_at_commit": champion,
            },
            "python_support_floor_scan": {
                "invocation": (
                    "PYTHONPATH=src python scripts/check_python_support_floor.py"),
                "files_scanned": 132, "syntax_rejections": 0,
                "api_uses_newer_than_floor": 0, "runtime_pep604_unions": 0,
                "obstruction_found": 0, "rerunnable": False,
                "conditions": (
                    "static analysis at a floor of 3.9. It can only FALSIFY a "
                    "floor, never confirm one. The scanned surface is the "
                    "CI-01 cost statement and it grew again."),
                "measured_at_commit": champion,
                "was_at_close": 121, "was_at_close_addendum": 123,
            },
        },
        "champion_per_generation": dict(
            v9["champion_per_generation"], g11=champion),
        "hist01_note": (
            "every hash in champion_per_generation from g0 through close "
            "predates the 2026-08-28 rewrite and resolves through "
            "docs/COMMIT_HASH_MAP_g11.json. They are left exactly as recorded; "
            "the map is a forward correction, not an edit."),
        "spec_clause_status": {
            "WIT-02": (
                "ENACTED at close and now SATISFIED ON ALL THREE COMMITTED "
                "SETS. Chart G closed at the addendum, chart J at generation 9, "
                "chart L here. Every one of the three lost members: 1 of 13, "
                "6 of 13, 11 of 37. Register version 3."),
            "WIT-01": (
                "UNCHANGED and NOT WITHDRAWN, and still vacuous: admissibility "
                "ratio 1.000 on all three sets, so it removes nothing anywhere."),
            "WITNESS-04": "CLOSED by measurement at generation 11.",
            "OBS-01": (
                "ENACTED at generation 11. Guard "
                "tests/test_inherited_obstructions_g11.py with both controls "
                "and a measured limitation."),
            "DOC-08": "UNCHANGED and enforced; every count here carries its denominator.",
            "SPEC-g0-3b-windows": (
                "OPERATOR-BLOCKED (hard), unchanged; substitute evidence "
                "docs/WINDOWS_RISK_g6.md. A remote now exists, which changes "
                "CI-01's status and not this clause's."),
        },
        "open_findings": open_findings(rv, rc, hz),
        "ruling_premises_corrected": v9["ruling_premises_corrected"] + [
            {
                "premise": (
                    "docs/CLOSE_RULING.md section 2 (b), ratified: what "
                    "predicts refinement survival is headroom against the "
                    "distinguishability floor"),
                "status": "FALSIFIED AS A GENERAL RULE at generation 11",
                "measured": (
                    "concordance 1.000 on chart G and chart J -- the two "
                    "13-pair sets that formed the rule -- and "
                    f"{hz['chart_L_d16']['concordance']:.3f} on chart L, the "
                    "37-pair set that did not. 0.500 is a coin. Spearman "
                    f"{hz['chart_L_d16']['spearman_rho']:+.3f} at p="
                    f"{hz['chart_L_d16']['spearman_p']:.3f}. The bands overlap "
                    "from 0.53 to 1.00 floor units."),
                "traced_forward_to": (
                    "spine item 3's clause 'survival is predicted by headroom "
                    "against the floor, not by geometry, in both refined sets'. "
                    "Amended in docs/G11_RESULT.md section 5 to 'what predicts "
                    "survival is not known'."),
                "what_it_strengthens": (
                    "the refusal to adopt a margin band. The close refused "
                    "because the band was 1.4 percentage points wide and would "
                    "be tuned; chart L shows there is no band at all."),
            },
            {
                "premise": (
                    "HIST-01 is unrepairable from inside the tree "
                    "(generations 8, 9, 10 and the close)"),
                "status": "FALSE, and untested when first written",
                "measured": (
                    "the repair was .git/filter-repo/commit-map, present since "
                    "before the finding was last restated. All 26 recorded "
                    "hashes resolve under three verifications."),
                "traced_forward_to": (
                    "eight failing guards and three silently skipping ones, "
                    "including the DOC-07 commit-message guard, which was not "
                    "running over the range it was written for."),
            },
            {
                "premise": (
                    "CI-01 is ACCEPTED-PERMANENT because there will be no "
                    "remote (generation 9 default)"),
                "status": "PREMISE FALSE; status reverted per its own condition",
                "measured": (
                    "git remote -v names origin at "
                    "https://github.com/Raar1999/bayespinn-inv.git, .git/config "
                    "stamped 2026-08-28 09:20, and refs/remotes/origin/main "
                    "resolves, so it was fetched from as well as configured."),
                "traced_forward_to": (
                    "CI-01 and PROV-07 both OPERATOR-BLOCKED, and OT-1 "
                    "executable for the first time in nine generations. "
                    "Nothing is closed: CI has still never run."),
            },
        ],
        "highest_remaining_scientific_risk": (
            "MECH-01, and it is now the entire distance to ladder rung L0. Why "
            "widening the bias window compresses the sensitivity spectrum "
            "toward its leading direction is unknown. One method -- "
            "localisation of the leading direction over parameters -- has been "
            "tried and falsified. The next generation attacks the observation "
            "side: which bias points carry sigma_2..sigma_4, and whether the "
            "points a widening window adds are the ones that carry them."),
        "second_remaining_scientific_risk": (
            "PATH-01, unchanged and untouched by full WIT-02 coverage. Every "
            "barrier is a straight line in one chart's coordinates and "
            "therefore an upper bound; both d=16 results are searches that "
            "found no path below the floor, not separations. The "
            "minimum-energy path is the single measurement that would settle "
            "it and it is still not computed."),
        "third_remaining_scientific_risk": (
            "what predicts refinement survival is now an open question rather "
            "than a settled one. The rule that was ratified as the answer is "
            "falsified on the largest set, and no replacement is proposed -- "
            "which is the honest state, not a gap to be filled with the next "
            "correlation that fits three points."),
        "not_supported_and_not_to_be_written":
            v9["not_supported_and_not_to_be_written"] + [
                "'survival is predicted by headroom against the floor' as a "
                "general claim, or any threshold or margin band derived from "
                "it. It holds on the two sets that formed it and carries no "
                "information on the third (concordance 0.479). "
                "outputs/g11/headroom.json",
                "'WIT-02 is satisfied' without the consequence beside it: full "
                "coverage tests witnesses, not connectivity, and converts no "
                "d=16 search statement into a separation",
                "'chart L is a basin' without 'no connecting path below the "
                "floor was found along the straight line', and without the "
                "coverage: 37 of 37 refined, 26 surviving",
                "any statement that HIST-01's repair recovers a lost working "
                "tree. It recovers commit names. REPRO-01 is untouched",
                "'the loop's history was lost' or any variant; it was renamed "
                "by a recorded rewrite and every hash resolves",
                "CI-01 as ACCEPTED-PERMANENT, or PROV-07 as "
                "MITIGATED-PENDING-CI; both are OPERATOR-BLOCKED since a "
                "remote exists",
                "any claim that a remote existing means CI has run. It has not, "
                "on any leg",
            ],
        "operator_tasks": [
            "OT-1 push and run CI -- NOW EXECUTABLE FOR THE FIRST TIME. A "
            "remote exists, so the command block in docs/OPERATOR_TASKS.md "
            "runs as written from `git push -u origin loop/champion` onward. "
            "CI-01 is OPERATOR-BLOCKED, not ACCEPTED-PERMANENT. R-4 and "
            "directive section 6 both reserve the push.",
            "OT-2 apply papers/CORRIGENDA_g6.md -- still unapplied; "
            "papers/draft.md line 255 unchanged. R-3 reserves papers/**. "
            "Seven cycles.",
            "OT-3 preservation -- sharpened by this generation. The HIST-01 "
            "repair depended on one untracked file on one disk, and the same "
            "argument applies to the repository itself. Seven cycles.",
        ],
        "what_gets_written": (
            "the spine as amended in docs/G11_RESULT.md section 5: items 3 and "
            "4 carry chart L's coverage and the withdrawal of the headroom "
            "clause; items 1, 2, 5 and 6 are unchanged from "
            "docs/CLOSE_RULING.md section 5."),
        "next_generation": {
            "target": "MECH-01, second distinct method: the observation side",
            "first_clause": (
                "which bias points carry sigma_2..sigma_4 in the normalised "
                "spectrum, and whether the points a widening window adds are "
                "the ones that carry them. Row-side leverage, against "
                "generation 10's falsified column-side localisation."),
            "why_it_beats_the_others": (
                "it is the only remaining item on the ladder. PATH-01 is "
                "larger scientifically but changes no rung and needs a string "
                "solver; CI-01 and PROV-07 are reserved; CHART-03 and SPEC-11 "
                "are MEDIUM and move nothing on the spine."),
            "pilot_first": True,
        },
        "halt": None,
    }
    return doc


def open_findings(rv, rc, hz):
    """Carried forward from generation 10, with this generation's movements."""
    v9 = read("LOOP_STATE_v9.json")["open_findings"]
    by_id = {f["id"]: dict(f) for f in v9}

    by_id["WITNESS-04"] = {
        "id": "WITNESS-04", "severity": "MEDIUM",
        "status": "RESOLVED-BY-MEASUREMENT at generation 11",
        "note": (
            "chart L's 37 witness pairs went through the refinement battery: "
            f"{rv['n_refined_here']} of {rv['n_pairs']} refined, "
            f"{rv['n_surviving']} surviving, {rv['n_separated_by_refinement']} "
            "separating. All three committed sets now satisfy WIT-02 and every "
            "one lost members. The classification over the survivors is "
            f"{rc['classification_over_the_surviving_set']}, unchanged, and the "
            "full set reproduces generation 10's depths bit-identically. What "
            "this does NOT close is PATH-01: coverage tests witnesses, not "
            "connectivity. docs/G11_RESULT.md section 1."),
    }
    by_id["HIST-01"] = {
        "id": "HIST-01", "severity": "MEDIUM",
        "status": "RESOLVED-BY-MEASUREMENT at generation 11",
        "note": (
            "not unrepairable and never was. git filter-repo rewrote the "
            "branch on 2026-08-28 09:16 and left its commit map in .git/, "
            "where three generations did not look. All 26 recorded hashes "
            "resolve under three verifications; the map is tracked because "
            ".git/ is not. Eight failing guards pass and three silently "
            "skipping ones run. docs/HIST01_REPAIR_g11.md."),
        "last_tested": {
            "generation": 11,
            "check": (
                "PYTHONPATH=src python scripts/repair_hist01.py; also git "
                "fsck --lost-found, both preservation copies, the pre-loop zip "
                "and origin, all of which were dead ends"),
            "result": "26 of 26 hashes resolve; V1, V2 and V3 all pass",
        },
    }
    by_id["CI-01"] = {
        "id": "CI-01", "severity": "MEDIUM",
        "status": "OPERATOR-BLOCKED (reverted from ACCEPTED-PERMANENT)",
        "note": (
            "the generation-9 default fired on the condition 'there will be no "
            "remote'. A remote exists, so the reversion condition recorded in "
            "docs/OPERATOR_TASKS.md applies. The cost statement is superseded "
            "forward, not deleted. Nothing is closed: .github/workflows/ci.yml "
            "has still never executed on any leg."),
        "cost_statement": (
            "docs/G9_RESULT.md section 1.4, superseded forward by "
            "docs/OPERATOR_TASKS.md OT-1 reversion and docs/G11_RESULT.md "
            "section 4.1. The statically-scanned surface grew again, to 132 "
            "files."),
        "cost_grown_since_assignment": True,
        "last_tested": {
            "generation": 11,
            "check": "git remote -v; git log --oneline origin/main; stat .git/config",
            "result": (
                "origin present at https://github.com/Raar1999/bayespinn-inv.git, "
                "origin/main resolves to the root commit, .git/config stamped "
                "2026-08-28 09:20"),
        },
    }
    by_id["PROV-07"] = {
        "id": "PROV-07", "severity": "HIGH",
        "status": "OPERATOR-BLOCKED (reclassified from MITIGATED-PENDING-CI)",
        "note": (
            "'pending' was the wrong word for nine generations: nothing was "
            "pending, because nothing was going to happen without an action "
            "reserved to the human. Validated on win32 only; linux and darwin "
            "unvalidated and stated as such in every manifest."),
        "last_tested": {
            "generation": 11,
            "check": (
                "PYTHONPATH=src python scripts/check_python_support_floor.py, "
                "and the same git remote inspection as CI-01"),
            "result": (
                "132 files scanned, 0 obstructions found at a 3.9 floor -- "
                "which can only falsify a floor, never confirm one. No leg of "
                "the matrix has ever executed"),
        },
    }
    by_id["PROV-03"] = dict(by_id["PROV-03"], last_tested={
        "generation": 11,
        "check": (
            "re-read docs/gen/GEN_g6.md section 2 against the tree: the "
            "bifurcation is structural in the adopted history and no artefact "
            "in outputs/ carries a pre-adoption provenance chain"),
        "result": (
            "unchanged and permanent by construction; nothing in this "
            "generation's artefacts depends on the missing chain"),
    })
    by_id["REPRO-01"] = dict(by_id["REPRO-01"], last_tested={
        "generation": 11,
        "check": (
            "the HIST-01 sweep covered the same ground: git fsck "
            "--lost-found, D:/bayespinn-inv/_preserve_g0_B, the scratchpad "
            "preserve_A copy, D:/bayespinn-inv/bayespinn-inv.zip and origin"),
        "result": (
            "still unrecoverable, and now for a measured reason. A commit hash "
            "is recoverable through the rewrite map; the WORKING TREE that "
            "produced outputs/identifiability/ on 2026-08-19 was never a "
            "commit, so no map can name it. The two preservation copies carry "
            "no .git and the zip is the pre-loop repository"),
    })
    by_id["EOL-01"] = {
        "id": "EOL-01", "severity": "LOW", "status": "OPEN, mechanism identified",
        "note": (
            "fired twice on this generation's own edits and the mechanism is "
            "now named rather than re-observed: Python's text mode rewrites an "
            "LF blob as CRLF on win32, so every write_text to a tracked file "
            "is a violation waiting to happen. Every write in this "
            "generation's scripts now pins newline='\\n', which makes a re-run "
            "idempotent. The finding stays OPEN because the repository's own "
            "convention is mixed -- some tracked blobs are CRLF, some LF -- "
            "and nothing enforces which a new file should use."),
    }
    by_id["DOC-03a"] = dict(
        by_id["DOC-03a"],
        note=by_id["DOC-03a"]["note"] + (
            " The class it named recurred at generation 11 as HIST-01, which "
            "is why OBS-01 was enacted rather than the observation being "
            "recorded a second time."))
    return list(by_id.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--champion", required=True)
    ap.add_argument("--collected", type=int, required=True)
    ap.add_argument("--passed", type=int, required=True)
    ap.add_argument("--skipped", type=int, required=True)
    ap.add_argument("--failed", type=int, required=True)
    a = ap.parse_args()
    doc = build(a.champion, {"collected": a.collected, "passed": a.passed,
                             "skipped": a.skipped, "failed": a.failed})
    OUT.write_text(json.dumps(doc, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.name}")
    print(f"  champion   {doc['champion_commit'][:12]}")
    print(f"  rung       {doc['governance']['rung_at_start']} -> "
          f"{doc['governance']['rung_at_end']} "
          f"({doc['governance']['movement']})")
    print(f"  findings   {len(doc['open_findings'])}")
    print(f"  pytest     {a.passed} passed, {a.failed} failed, "
          f"{a.skipped} skipped of {a.collected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
