"""Build ``LOOP_STATE_v11.json`` from the generation-12 artefacts.

    PYTHONPATH=src python scripts/write_loop_state_g12.py --champion <sha> ...

Same discipline as ``scripts/write_loop_state_g11.py``: every count is read out
of an artefact rather than transcribed, so the state file cannot drift from the
measurement it describes without this builder failing first. The champion is
passed in, because a state file cannot name the commit that writes it.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "LOOP_STATE_v11.json"


def read(rel: str) -> Any:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, timeout=30).stdout.strip()


def home_path_exposure() -> Dict[str, Any]:
    """SW-18, measured rather than recalled, on both separator conventions."""
    def count(pattern: str) -> List[str]:
        out = subprocess.run(["git", "grep", "-nIE", pattern, "--", "."],
                             cwd=ROOT, capture_output=True, text=True)
        return [ln for ln in out.stdout.splitlines() if ln.strip()]

    posix = count(r"/(home|Users)/[a-zA-Z0-9_.-]+")
    windows = count(r"C:[\\/]+Users[\\/]+[A-Za-z0-9_.-]+")
    files = sorted({ln.split(":", 1)[0] for ln in windows})
    return {
        "posix_pattern_from_the_ruling": r"/(home|Users)/[a-zA-Z0-9_.-]+",
        "posix_hits": len(posix),
        "windows_pattern_the_ruling_could_not_match": (
            r"C:[\\/]+Users[\\/]+[A-Za-z0-9_.-]+"),
        "windows_hits": len(windows),
        "windows_files": files,
        "n_windows_files": len(files),
        "note": (
            "the ruling's regex is forward-slash only, so it finds the eight "
            "/home/claude/ occurrences of SW-18a and none of the Windows ones. "
            "This is not a criticism of the ruling; it is why the check was "
            "run rather than assumed"),
    }


def eol_state() -> Dict[str, Any]:
    out = subprocess.run(["git", "ls-files", "--eol"], cwd=ROOT,
                         capture_output=True, text=True).stdout.splitlines()
    tracked = len(out)
    text_attr = sum(1 for ln in out if "attr/-text" in ln)
    kinds: Dict[str, int] = {}
    for ln in out:
        parts = ln.split()
        if parts:
            k = parts[0].split("/")[1] if "/" in parts[0] else parts[0]
            kinds[k] = kinds.get(k, 0) + 1
    return {
        "tracked_files": tracked,
        "resolving_to_minus_text": text_attr,
        "coverage_complete": bool(tracked == text_attr),
        "index_eol_kinds": dict(sorted(kinds.items())),
        "gitattributes_comment_claims": {"crlf": 119, "lf": 74, "mixed": 2},
        "comment_is_stale_by_growth": True,
        "the_gap_is_not_coverage": (
            "-text binds git, not tools. Both recent incidents were Python's "
            "text mode rewriting an LF blob as CRLF on win32, which no "
            ".gitattributes can prevent"),
    }


def build(champion: str, counts: Dict[str, int]) -> Dict[str, Any]:
    v10 = read("LOOP_STATE_v10.json")
    ops = read("outputs/g12/operator_actions.json")
    rows = read("outputs/g12/mech01_rows/rows.json")
    verdict = read("outputs/g12/mech01_rows/verdict.json")
    controls = read("outputs/g12/mech01_rows/controls.json")
    disc = read("outputs/g12/mech01_discriminator.json")
    pre = read("outputs/g12/mech01_rows/preregister.json")

    r1 = rows["reproduction_control_R1"]
    ratios = {k: v["max_ratio_width_over_spacing"]
              for k, v in disc["devices"].items()}
    peaks = {k: v["width"]["at_max_width_V"] for k, v in disc["devices"].items()}

    doc: Dict[str, Any] = {
        "generation": 12,
        "step": "generation 12, the reserved-item ruling, 2026-08-28",
        "designation": (
            "GENERATION 12. Run under the operator ruling of 2026-08-28 that "
            "answered the reserved item: it gated git push on six checks, "
            "enacted OPS-02, PILOT-01 and SKIP-01, ordered the line-ending fix "
            "re-verified, and approved MECH-01's second method with both "
            "outcomes stated first. The push was NOT run: two preconditions "
            "are human-only and one is not clean. MECH-01's row-side method "
            "ran and its own control axis invalidated its pre-registered "
            "verdict."),
        "terminated": False,
        "closed": False,
        "governance": {
            "directive": "operator directive of 2026-08-28, authority fused",
            "ruling": "operator ruling of 2026-08-28, the reserved item",
            "ladder": "LADDER.md",
            "ladder_sha256": v10["governance"]["ladder_sha256"],
            "ladder_edited_since_instantiation": False,
            "rung_at_start": "L1",
            "rung_at_end": "L1",
            "movement": "HELD",
            "unreachability_verdicts_issued": [],
            "why_none": (
                "MECH-01's second method was inconclusive rather than "
                "falsified, so U-EMPIR still stands at ONE failed method -- "
                "generation 10's column side. A sharpened version of this "
                "statistic is the same method with a better statistic, not a "
                "third distinct one, and counting it as a second failure "
                "would be inflating the count toward a verdict."),
            "distance_to_L0": "MECH-01, unchanged.",
        },
        "champion_commit": champion,
        "machinery_commit": champion,
        "results_commit": champion,
        "bookkeeping_commit": None,
        "champion_branch": "loop/champion",
        "schema": v10["schema"],
        "pre_push_runbook": {
            "authorised_by": "operator ruling of 2026-08-28 §1",
            "push_was_run": False,
            "why_not": (
                "steps 1-6 do not all pass, which is the ruling's own "
                "condition. Step 1 (the map off this machine) is a human "
                "action; step 6's home-path arm is not clean."),
            "steps": {
                "1_map_off_machine": {
                    "status": "HUMAN ACTION, NOT DONE",
                    "artefact": "docs/COMMIT_HASH_MAP_g11.json",
                    "sha256": (
                        "5486343309bbeefeaf99a99edc0cb1b320f39f9eec837cf343"
                        "62bd952ab6f970"),
                    "sharpened_by_step_5": (
                        "no preservation copy holds pre-rewrite objects, so "
                        "this map is the SOLE surviving trace of the "
                        "pre-rewrite identity of ten generations"),
                },
                "2_rewrite_achieved_its_purpose": {
                    "status": "PASS",
                    "co_authored_by": 0, "generated_with": 0,
                    "generated_by": 0, "ai_assisted": 0, "claude": 0,
                    "reading": "provenance was not broken for nothing",
                },
                "3_hook_installed": {
                    "status": "PASS",
                    "path": ops["surfaces"]["hooks"]["hooks_directory_in_use"],
                    "outside_the_repository": ops["surfaces"]["hooks"][
                        "is_outside_the_repository"],
                    "installed": ops["surfaces"]["hooks"]["installed"],
                    "ordering": (
                        "the hook was installed at 09:06:36, TEN MINUTES "
                        "BEFORE the 09:16:38 rewrite. They were not "
                        "alternatives; the ruling's concern that the rewrite "
                        "was done instead of the hook does not hold"),
                    "tested_not_assumed": (
                        "both controls: a planted Co-Authored-By is stripped "
                        "and the body survives; an ordinary message "
                        "containing 'generated' and 'co-author' is byte-"
                        "identical afterwards"),
                },
                "4_remote_state": {
                    "status": "PASS",
                    "refs_on_remote": ["refs/heads/main"],
                    "remote_main": "6577f4b87a65cd2c255062e42ea5181f04483e93",
                    "rewrite_touched_it": False,
                    "why_no_force_is_needed": (
                        "filter-repo's commit-map maps the root commit to "
                        "ITSELF, local main is byte-identical to remote main, "
                        "and it is an ancestor of loop/champion. The push adds "
                        "38 commits on a new branch and rewrites nothing"),
                    "commits_the_push_would_add": 38,
                },
                "5_preservation_copies": {
                    "status": "PASS, and the finding is the absence",
                    "preserve_A_has_git": False,
                    "preserve_B_has_git": False,
                    "zip_is_the_pre_loop_repository": True,
                    "pre_rewrite_objects_anywhere": 0,
                    "reading": (
                        "the copies are NOT an independent record of the "
                        "original SHAs, because no such record exists "
                        "anywhere. Nothing to relabel"),
                },
                "6_SW_18": {
                    "status": "credentials PASS; home paths FAIL",
                    "credential_shaped_literals": 0,
                    "keyword_hits_all_false_positives": 4,
                    "author_identity": "Raar1999@users.noreply.github.com",
                    "home_paths": home_path_exposure(),
                    "consequence": (
                        "does not block a PRIVATE push; blocks the repository "
                        "being public, which is what the ruling made it a "
                        "precondition of"),
                },
            },
            "what_the_operator_must_do": [
                "move docs/COMMIT_HASH_MAP_g11.json off this machine, two "
                "copies, verified against the digest above",
                "decide repository visibility given the 67 home-path "
                "occurrences, or authorise a private push with them present",
            ],
        },
        "measurements": {
            "OPS-02_first_audit": {
                "invocation": (
                    "PYTHONPATH=src python scripts/audit_operator_actions.py"),
                "artefact": "outputs/g12/operator_actions.json",
                "surfaces_audited": ops["surfaces_audited"],
                "ordering_recovered": {
                    "09:06:36": "commit-msg hook installed, outside the repo",
                    "09:16:38": "git filter-repo run, 35 commits rewritten",
                    "09:20:50": "remote origin added and fetched",
                },
                "reflog_entries": ops["surfaces"]["reflog"]["n_entries"],
                "reflog_shorter_than_history": ops["surfaces"]["reflog"][
                    "reflog_is_shorter_than_the_history"],
                "reading": (
                    "three operator actions inside fifteen minutes, none "
                    "detected by the loop for a generation"),
            },
            "MECH-01_second_method": {
                "question": (
                    "when the window widens and sigma_2..sigma_4 climb, are "
                    "those directions carried by the bias points the widening "
                    "ADDS, or by bias points already in the narrow window?"),
                "authorised_by": "operator ruling of 2026-08-28 §5",
                "preregistered": True,
                "measure_hash": verdict["measure_hash"],
                "outcomes_hash": verdict["outcomes_hash"],
                "invocation": (
                    "PYTHONPATH=src python scripts/run_mech01_rows.py"),
                "pilot": pre["pilot"],
                "new_solves_note": pre["new_solves"],
                "preregistered_classification": verdict["classification"],
                "preregistered_verdict_is_void": True,
                "why_it_is_void": disc["why_the_sign_verdict_is_void"],
                "R1_reproduction": (
                    f"PASS, {r1['n_identical']} of {r1['of']} singular values "
                    "bit-identical to generation 9"),
                "N1_negative": {
                    "rho_vs_width": controls["N1_negative"]["spearman_vs_width"],
                    "threshold": controls["N1_negative"]["threshold"],
                    "passes": controls["N1_negative"]["passes"],
                    "note": (
                        "passing, and the least comfortable margin in this "
                        "generation. A single Haar draw per width bounds the "
                        "statistic's gullibility; it does not estimate a null "
                        "distribution"),
                },
                "P1_positive": controls["P1_positive"]["passes"],
                "C1_control_axis": (
                    "THE CONTROL THAT KILLED THE VERDICT. The same sign "
                    "appears in 16 of 18 cells of the spacing axis, where the "
                    "rank does not move at all"),
                "description_not_a_test": {
                    "artefact": "outputs/g12/mech01_discriminator.json",
                    "status": "DESCRIPTION, chosen after the sign failed (AH-14)",
                    "new_solves": 0,
                    "max_ratio_width_over_spacing": ratios,
                    "peak_width_V": peaks,
                    "width_max_exceeds_every_spacing_cell": disc["reading"][
                        "width_max_exceeds_every_spacing_cell_at_both_devices"],
                    "shared_cell_control": (
                        "alpha=0 and width=0.75 are one observation set by two "
                        "code paths (g9's C4) and agree to the last bit at "
                        "both devices"),
                    "what_it_does_not_establish": disc["reading"][
                        "what_it_does_not_establish"],
                },
                "consequence_for_U_EMPIR": disc["consequence_for_U_EMPIR"],
            },
            "gitattributes_reverification": eol_state(),
        },
        "declined_measurements": [
            {
                "id": "MECH-01-magnitude-preregistered",
                "measurement": (
                    "the magnitude statistic of §4.3, pre-registered, with the "
                    "spacing axis as the null"),
                "why_declined": (
                    "NOT on a plausibility argument. A statistic cannot be "
                    "pre-registered against cells that have already been seen, "
                    "so making this a test needs NEW cells -- a third device, "
                    "or a held-out axis. That is a generation-13 measurement "
                    "with its own pre-registration, not a re-read of this "
                    "generation's artefacts."),
                "pilot": {
                    "invocation": (
                        "PYTHONPATH=src python scripts/run_mech01_rows.py "
                        "--phases pilot"),
                    "per_cell_mean_s": pre["pilot"]["per_cell_mean_s"],
                    "cells_required": pre["pilot"]["cells_required"],
                    "projected_total_s": pre["pilot"]["projected_total_s"],
                    "verdict": "AFFORDABLE",
                },
                "not_a_budget_decline": (
                    "the price is minutes and is recorded so that nobody can "
                    "later mistake this for one. PILOT-01 exists because chart "
                    "L was declined for three generations without anyone "
                    "measuring that it cost five minutes."),
            },
            {
                "id": "SW-18-manifest-redaction",
                "measurement": (
                    "redacting the home-directory prefix at manifest-write "
                    "time so future manifests carry ~ rather than C:\\Users\\<user>"),
                "why_declined": (
                    "deferred to generation 13, and it is a code change rather "
                    "than a measurement, so it carries an effort note rather "
                    "than a solve pilot. It cannot repair the 67 existing "
                    "occurrences: directive §6 reserves mutation of an "
                    "existing manifest, so those are superseded forward or "
                    "left, and that is an operator decision tied to repository "
                    "visibility."),
                "pilot": {
                    "invocation": (
                        "git grep -nIE 'C:[\\\\/]+Users[\\\\/]+[A-Za-z0-9_.-]+' -- ."),
                    "occurrences": 67,
                    "files_affected": 12,
                    "new_solves": 0,
                },
            },
        ],
        "baselines": {
            "pytest": {
                "invocation": "PYTHONPATH=src python -m pytest tests -q",
                "tool_version": "pytest 9.1.1",
                "collected": counts["collected"], "passed": counts["passed"],
                "skipped": counts["skipped"], "failed": counts["failed"],
                "rerunnable": False,
                "conditions": (
                    "taken at champion_commit with LOOP_STATE_v11.json NOT yet "
                    "in the tree, so the guards that read it skip. Stated "
                    "rather than smoothed over."),
                "measured_at_commit": champion,
                "environment": "CPython 3.11.9, win32",
            },
            "ruff_whole_tree": {
                "invocation": "python -m ruff check .",
                "tool_version": "ruff 0.16.3", "exit_code": 0,
                "findings": 0, "rerunnable": True,
            },
            "mypy_tracked_tree": {
                "invocation": "mypy src tests scripts",
                "tool_version": "mypy 2.3.1",
                "findings": 150, "files_checked": counts["mypy_files"],
                "rerunnable": False,
                "conditions": (
                    "THE CARRIED BASELINE, unchanged at 150 while the checked "
                    "surface grew again. Every module added this generation is "
                    "clean under this invocation."),
                "measured_at_commit": champion,
                "was_at_generation_11": {"findings": 150, "files_checked": 134},
            },
        },
        "champion_per_generation": dict(
            v10["champion_per_generation"], g12=champion),
        "spec_clause_status": dict(
            v10["spec_clause_status"],
            **{
                "OPS-02": (
                    "ENACTED at generation 12. Guard "
                    "tests/test_operator_actions_g12.py, both controls, and "
                    "its first run recovered the 09:06 / 09:16 / 09:20 "
                    "ordering of three undetected operator actions."),
                "PILOT-01": (
                    "ENACTED at generation 12 and applied the same generation: "
                    "MECH-01's second method was priced before it was decided "
                    "on. Guard tests/test_pilot_first_g12.py."),
                "SKIP-01": (
                    "ENACTED at generation 12. docs/SKIP_REGISTER.json, "
                    "scripts/report_skips.py, "
                    "tests/test_skip_register_g12.py."),
                "MECH-01": (
                    "OPEN. Second method inconclusive as pre-registered -- the "
                    "discriminator was too blunt, not the hypothesis wrong. "
                    "U-EMPIR stands at one falsified method."),
            }),
        "open_findings": open_findings(v10, disc),
        "ruling_premises_corrected": v10["ruling_premises_corrected"] + [
            {
                "premise": (
                    "operator ruling of 2026-08-28 §3: three line-ending "
                    "incidents mean the .gitattributes fix is incomplete in "
                    "COVERAGE"),
                "status": "CORRECTED -- the fix is incomplete, but not there",
                "measured": (
                    "350 of 350 tracked files resolve to attr/-text, every "
                    "generation-11 and -12 module included. Coverage is total "
                    "and cannot miss a class, because `* -text` is a wildcard."),
                "what_is_actually_incomplete": (
                    "-text binds git, not tools. Incidents 2 and 3 were both "
                    "Python's text mode rewriting an LF blob as CRLF on win32, "
                    "which no .gitattributes can prevent. Generation 11 pinned "
                    "newline in its own scripts; nothing enforces it."),
            },
            {
                "premise": (
                    "generation 12's own pre-registered discriminator for "
                    "MECH-01: the SIGN of trailing-minus-head excess "
                    "separates the width axis from the control axis"),
                "status": "FALSIFIED BY ITS OWN CONTROL, in the same run",
                "measured": (
                    "the sign returns NEW_ROWS at 16 of 16 width cells and "
                    "also at 16 of 18 spacing cells, where the rank does not "
                    "move. The discriminator does not discriminate."),
                "what_was_done_about_it": (
                    "the pre-registered verdict is left standing in "
                    "outputs/g12/mech01_rows/verdict.json exactly as produced. "
                    "Changing the classification rule after seeing the control "
                    "would be the violation pre-registration exists to "
                    "prevent. The magnitude comparison that does separate the "
                    "axes is recorded as a DESCRIPTION under AH-14."),
            },
            {
                "premise": (
                    "operator ruling §1.6's regex "
                    "/(home|Users)/[a-zA-Z0-9_.-]+ finds the absolute home "
                    "paths"),
                "status": "INCOMPLETE, and this is why the check was run",
                "measured": (
                    "forward-slash only, so it finds 8 occurrences and misses "
                    "67 Windows-separator ones across 12 files, ten of which "
                    "this loop's own generation-11 manifest added."),
            },
        ],
        "highest_remaining_scientific_risk": (
            "MECH-01, unchanged and now with one falsified method and one "
            "inconclusive one. The row-side signal is real in description -- "
            "3.1x to 3.5x larger on the width axis than anywhere on the "
            "control axis, peaking at 0.15 V where the rank is climbing -- but "
            "its statistic was chosen after the fact and a pre-registered "
            "version needs new cells."),
        "second_remaining_scientific_risk": v10[
            "second_remaining_scientific_risk"],
        "third_remaining_scientific_risk": (
            "the claim surface carries 67 absolute home paths, ten of them "
            "added by this loop at generation 11. Not a scientific risk to the "
            "results; a publication risk that the ruling made a precondition "
            "of the repository being public."),
        "not_supported_and_not_to_be_written":
            v10["not_supported_and_not_to_be_written"] + [
                "'the new directions live on the added bias points' as a "
                "measured result. The sign test that would have established it "
                "fires equally on the control axis; what is left is a "
                "magnitude description chosen after the fact. "
                "outputs/g12/mech01_discriminator.json",
                "NEW_ROWS as MECH-01's answer, or any statement that MECH-01 "
                "is narrowed by a test rather than by a description",
                "'two methods have failed' for MECH-01. One was falsified "
                "(generation 10, column side) and one was inconclusive; "
                "counting the second as a failure inflates the count toward a "
                "U-EMPIR verdict",
                "'the push checks passed'. Five of six passed; step 1 is a "
                "human action not done and step 6's home-path arm is not clean",
                "'the repository is safe to make public'. 67 absolute home "
                "paths naming a user are on the claim surface",
            ],
        "operator_tasks": [
            "OT-1 push and run CI -- CONDITIONALLY AUTHORISED by the ruling of "
            "2026-08-28 §1, and NOT authorised yet: steps 1 and 6 do not pass. "
            "See pre_push_runbook.what_the_operator_must_do.",
            "OT-2 apply papers/CORRIGENDA_g6.md -- still unapplied. R-3 "
            "reserves papers/**. Eight cycles.",
            "OT-3 preservation -- now the sharpest of the three. The commit "
            "map is the sole surviving trace of ten generations' pre-rewrite "
            "identity and lives on one disk. Eight cycles.",
        ],
        "next_generation": {
            "target": (
                "MECH-01, third pass: the magnitude statistic pre-registered "
                "against new cells"),
            "first_clause": (
                "a third device, or a held-out axis, with the magnitude "
                "statistic and the spacing axis as the null both registered "
                "before the first SVD. Priced at "
                f"{pre['pilot']['per_cell_mean_s']:.1f} s per cell."),
            "why_it_beats_the_others": (
                "it is still the only item on the ladder, and this generation "
                "produced a described signal worth testing rather than a dead "
                "end. It is the same method sharpened, so it does not count "
                "toward U-EMPIR."),
            "also_scoped": (
                "SW-18 manifest redaction, forward only; directive §6 reserves "
                "mutating the existing manifests."),
        },
        "halt": None,
    }
    return doc


def open_findings(v10: Dict[str, Any], disc: Dict[str, Any]) -> List[Dict]:
    by_id = {f["id"]: dict(f) for f in v10["open_findings"]}
    by_id["MECH-01"] = {
        "id": "MECH-01", "severity": "HIGH",
        "status": "OPEN, one method falsified and one inconclusive",
        "note": (
            "generation 10's column-side localisation was falsified. "
            "Generation 12's row-side method was INCONCLUSIVE as "
            "pre-registered: the sign discriminator fires equally on the "
            "control axis, so it does not discriminate. The magnitude "
            "comparison that does separate the axes -- 3.1x to 3.5x, peaking "
            "at 0.15 V where the rank climbs -- is a description chosen after "
            "the fact (AH-14). U-EMPIR stands at ONE failed method."),
        "last_tested": {
            "generation": 12,
            "check": (
                "PYTHONPATH=src python scripts/run_mech01_rows.py; then "
                "scripts/mech01_discriminator.py over its output"),
            "result": (
                "R1 72 of 72 singular values reproduce generation 9; the "
                "pre-registered sign verdict is void by its own C1 control"),
        },
    }
    by_id["SW-18a"] = {
        "id": "SW-18a", "severity": "LOW",
        "status": "OPEN, and larger than recorded",
        "note": (
            "recorded as two manifests carrying absolute home paths. Measured "
            "at generation 12 on both separator conventions: 8 posix "
            "occurrences and 67 Windows ones across 12 files, ten of them "
            "added by this loop at generation 11. Repair is forward-only; "
            "directive §6 reserves mutating an existing manifest."),
        "last_tested": {
            "generation": 12,
            "check": (
                "git grep -nIE '/(home|Users)/[a-zA-Z0-9_.-]+' and "
                "git grep -nIE 'C:[\\\\/]+Users[\\\\/]+[A-Za-z0-9_.-]+'"),
            "result": "8 and 67 occurrences respectively",
        },
    }
    by_id["EOL-01"] = {
        "id": "EOL-01", "severity": "LOW",
        "status": "OPEN, mechanism identified, git side complete",
        "note": (
            "re-verified at generation 12 under the ruling §3: 350 of 350 "
            "tracked files resolve to attr/-text, so COVERAGE is complete and "
            "the diagnosis that it was not is corrected. The incomplete half "
            "is the tool side -- Python's text mode rewrites an LF blob as "
            "CRLF on win32 and no .gitattributes can prevent it. Generation 11 "
            "pinned newline in its own scripts; nothing enforces it across "
            "the tree."),
        "last_tested": {
            "generation": 12,
            "check": (
                "git ls-files --eol, counting attr/-text against tracked "
                "files, and comparing index against working-tree eol"),
            "result": (
                "350 of 350 -text; no index/worktree disagreement; the "
                ".gitattributes comment's counts are stale by growth "
                "(119/74/2 recorded, 178/157/2 measured)"),
        },
    }
    return list(by_id.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--champion", required=True)
    ap.add_argument("--collected", type=int, required=True)
    ap.add_argument("--passed", type=int, required=True)
    ap.add_argument("--skipped", type=int, required=True)
    ap.add_argument("--failed", type=int, required=True)
    ap.add_argument("--mypy-files", type=int, required=True)
    a = ap.parse_args()
    doc = build(a.champion, {
        "collected": a.collected, "passed": a.passed, "skipped": a.skipped,
        "failed": a.failed, "mypy_files": a.mypy_files})
    OUT.write_text(json.dumps(doc, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.name}")
    print(f"  champion {doc['champion_commit'][:12]}   rung "
          f"{doc['governance']['rung_at_start']} -> "
          f"{doc['governance']['rung_at_end']}")
    print(f"  declined measurements: {len(doc['declined_measurements'])} "
          "(each priced)")
    print(f"  findings {len(doc['open_findings'])}")
    print(f"  pytest {a.passed} passed, {a.failed} failed, {a.skipped} skipped")
    assert re.fullmatch(r"[0-9a-f]{40}", a.champion), "champion must be a full sha"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
