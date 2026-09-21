"""``OPS-02``: the Phase A audit of operator actions actually audits them.

Full text and the defect that forced it: ``docs/RULES_ENACTED.md``, ``OPS-02``.
The artefact is ``outputs/g12/operator_actions.json``, produced by
``scripts/audit_operator_actions.py``.

Why this guard is written the way it is
---------------------------------------
The failure mode for a detector is not that it reports the wrong thing. It is
that it runs, reports nothing, and everyone reads the silence as *nothing
happened*. That is exactly what the loop did for a generation while a rewrite
and a remote sat undetected in ``.git/``.

So the assertions here are mostly about **the audit being able to see**, not
about what it saw: every named surface is present, the surfaces that are
knowable from the filesystem agree with the filesystem, and the audit refuses to
call a surface absent when it is there.

``SW-20``: the subject is a JSON document; this module's own source is not part
of the scanned document, and both controls are below.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "outputs" / "g12" / "operator_actions.json"

#: The five surfaces `OPS-02` names. Missing one is the guard's whole point.
REQUIRED = ("remote", "config", "hooks", "filter_repo", "reflog")

pytestmark = pytest.mark.skipif(
    not AUDIT.is_file(),
    reason="outputs/g12/operator_actions.json not written yet; run "
           "PYTHONPATH=src python scripts/audit_operator_actions.py")


def git(*args: str) -> Optional[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                         text=True, timeout=30)
    return out.stdout.strip() if out.returncode == 0 else None


@pytest.fixture(scope="module")
def audit() -> Dict[str, Any]:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def missing_surfaces(doc: Dict[str, Any]) -> List[str]:
    got = doc.get("surfaces") or {}
    return [s for s in REQUIRED if s not in got]


def blind_surfaces(doc: Dict[str, Any]) -> List[str]:
    """Surfaces the audit reports as absent while the filesystem disagrees.

    This is the plausible failure -- an audit that runs and sees nothing --
    rather than the malformed one.
    """
    bad = []
    surfaces = doc.get("surfaces") or {}
    fr = surfaces.get("filter_repo") or {}
    if (ROOT / ".git" / "filter-repo").is_dir() and not fr.get("present"):
        bad.append("filter_repo reports absent while .git/filter-repo/ exists")
    rem = surfaces.get("remote") or {}
    if git("remote") and not rem.get("present"):
        bad.append("remote reports absent while git remote names one")
    hooks = surfaces.get("hooks") or {}
    path = git("config", "--get", "core.hooksPath")
    if path and not hooks.get("core_hooksPath"):
        bad.append("hooks reports no core.hooksPath while git config sets one")
    return bad


class TestTheAuditCoversEverySurfaceTheRuleNames:

    def test_no_surface_is_missing(self, audit) -> None:
        missing = missing_surfaces(audit)
        assert not missing, (
            f"OPS-02 names five surfaces; the audit omits {missing}. An audit "
            "that does not look at a surface reports the same silence as an "
            "audit that looked and found nothing")

    def test_the_audit_records_which_commit_it_was_taken_at(self, audit) -> None:
        assert audit.get("head"), "an audit that does not say which tree it read"
        assert audit.get("audited_at")

    def test_it_states_what_it_cannot_see(self, audit) -> None:
        text = (audit.get("what_it_cannot_see") or "").lower()
        assert "no trace" in text or "reverted" in text, (
            "the audit must name its blind spot. A detector that implies "
            "completeness is worse than one that states its limit")

    def test_it_does_not_judge(self, audit) -> None:
        assert audit.get("it_does_not_judge"), (
            "OPS-02 records what changed; whether an operator action was "
            "correct is the operator's authority, and a detector that "
            "editorialises is one people switch off")


class TestTheAuditIsNotBlind:
    """It must agree with the filesystem on the things the filesystem knows."""

    def test_it_sees_what_is_actually_there(self, audit) -> None:
        blind = blind_surfaces(audit)
        assert not blind, "the audit is blind to:\n  " + "\n  ".join(blind)

    def test_the_rewrite_is_recorded_if_it_happened(self, audit) -> None:
        fr = audit["surfaces"]["filter_repo"]
        if not (ROOT / ".git" / "filter-repo").is_dir():
            pytest.skip(
                "no filter-repo artefacts in this clone; SKIP-01 register entry "
                "'filter-repo absent' -- expires if .git/filter-repo reappears")
        assert fr["present"] is True
        assert fr.get("rewritten_commits", 0) > 0
        assert fr.get("tracked_copy_present") is True, (
            "the rewrite is recorded but its map is not tracked. .git/ is not "
            "tracked either, so the only bridge to ten generations of "
            "manifests would live in one place")

    def test_a_hook_path_outside_the_repository_is_flagged_as_such(
            self, audit) -> None:
        hooks = audit["surfaces"]["hooks"]
        path = hooks.get("core_hooksPath")
        if not path:
            pytest.skip(
                "core.hooksPath unset, so .git/hooks is in use; SKIP-01 "
                "register entry 'hooks path unset' -- expires if it is set")
        assert hooks["is_outside_the_repository"] is True, (
            "core.hooksPath points outside the repository and the audit did "
            "not say so. That is the surface an in-repository check misses")
        assert hooks["n_installed"] >= 1


class TestTheGuardHasBothControls:
    """``IA-1``. A plausible negative, and a positive that would fail if the
    rule did nothing."""

    def test_negative_control_an_audit_missing_a_surface_is_caught(
            self) -> None:
        planted: Dict[str, Any] = {
            "surfaces": {s: {} for s in REQUIRED if s != "reflog"}}
        assert missing_surfaces(planted) == ["reflog"]

    def test_negative_control_an_audit_that_runs_and_sees_nothing_is_caught(
            self) -> None:
        """The plausible failure, not the malformed one.

        Every surface present, every one reporting absent. This is what a
        detector looks like after someone 'fixes' it by making it stop
        complaining.
        """
        if not (ROOT / ".git" / "filter-repo").is_dir():
            pytest.skip(
                "control needs a real rewrite to be blind to; SKIP-01 register "
                "entry 'filter-repo absent'")
        planted: Dict[str, Any] = {"surfaces": {
            "remote": {"present": False},
            "config": {},
            "hooks": {"core_hooksPath": None},
            "filter_repo": {"present": False},
            "reflog": {},
        }}
        blind = blind_surfaces(planted)
        assert blind, "a wholly blind audit was not caught"
        assert any("filter_repo" in b for b in blind)

    def test_positive_control_the_real_audit_passes_both_predicates(
            self, audit) -> None:
        """Would fail if the predicates rejected everything."""
        assert missing_surfaces(audit) == []
        assert blind_surfaces(audit) == []


class TestWhatThisGenerationFound:
    """The audit's first live use reproduces the §1 findings, or it is not
    doing its job."""

    def test_it_reproduces_the_remote_that_nobody_noticed(self, audit) -> None:
        rem = audit["surfaces"]["remote"]
        if not rem["present"]:
            pytest.skip("no remote configured; SKIP-01 register entry "
                        "'no remote' -- expires when one is added")
        assert rem["n_remotes"] >= 1
        assert any("github.com" in u or "://" in u for u in rem["urls"])

    def test_it_reproduces_the_config_settings_that_define_a_commit(
            self, audit) -> None:
        watched = audit["surfaces"]["config"]["watched"]
        assert "core.autocrlf" in watched
        assert "core.hooksPath" in watched, (
            "core.hooksPath must be watched by name: it decides whether the "
            "repository's hooks are the ones that run")

    def test_the_reflog_truncation_is_visible(self, audit) -> None:
        rl = audit["surfaces"]["reflog"]
        assert "reflog_is_shorter_than_the_history" in rl, (
            "filter-repo expires the reflog, so a reflog shorter than the "
            "history is itself evidence of a rewrite and must be reported")
        assert os.path.isdir(ROOT / ".git")
