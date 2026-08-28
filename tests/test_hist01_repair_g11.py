"""``HIST-01``'s repair, guarded so it cannot silently rot back into a claim.

What is being guarded, and why it needs guarding
------------------------------------------------
``HIST-01`` was carried for three generations as **UNREPAIRABLE FROM INSIDE THE
TREE**. It was repairable from inside the tree the whole time: ``git
filter-repo`` rewrote this branch on 2026-08-28 and left
``.git/filter-repo/commit-map`` behind, and nobody looked. The repair is
``docs/COMMIT_HASH_MAP_g11.json``, built and verified by
``scripts/repair_hist01.py``.

A correction map is a dangerous kind of artefact, because it is the thing that
makes eight previously-failing guards pass. If it were wrong, or if it silently
degraded, it would convert a visible failure into an invisible one -- which is
strictly worse than the failure. So the map is guarded harder than the thing it
repairs.

``TestTheMapIsPresentAndTracked``
    the map has to be in the tree, not in ``.git/``. ``.git/filter-repo/`` is
    untracked, exists on one disk, and cannot be rebuilt once gone.

``TestTheMapVerifiesItself``
    all three verifications the builder runs must be recorded as passing. The
    resolver refuses an unverified map, so this pins that the recorded state is
    the passing one.

``TestTheMapActuallyResolvesWhatItClaims``
    re-derived here rather than read: every hash any ``LOOP_STATE`` file records
    is resolved through the public helper and must land on a real commit.

``TestTheResolverFailsClosed``
    the controls. ``IA-1`` wants a negative control that is *plausible* and a
    positive control that would fail if the rule did nothing.

``SW-20``: the subject is a JSON document and a helper module; this module's own
source is not part of the scanned document.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Optional

import pytest
from commit_map import MAP, is_real_commit, load_map, map_is_verified, resolve_commit

ROOT = Path(__file__).resolve().parents[1]
STATE_FILES = sorted(ROOT.glob("LOOP_STATE_v*.json"))
COMMIT_KEYS = ("champion_commit", "machinery_commit", "results_commit")


def git(*args: str) -> Optional[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                         text=True, timeout=30)
    return out.stdout.strip() if out.returncode == 0 else None


def recorded_hashes() -> List[tuple]:
    """Every commit hash any state file records, with where it came from."""
    found = []
    for path in STATE_FILES:
        doc = json.loads(path.read_text(encoding="utf-8"))
        for key in COMMIT_KEYS:
            val = doc.get(key)
            if isinstance(val, str) and len(val) >= 7:
                found.append((f"{path.name}:{key}", val))
        for gen, val in (doc.get("champion_per_generation") or {}).items():
            if isinstance(val, str) and len(val) >= 7:
                found.append((f"{path.name}:g{gen}", val))
    return found


pytestmark = pytest.mark.skipif(
    git("rev-parse", "HEAD") is None, reason="not a git checkout")


class TestTheMapIsPresentAndTracked:
    """The repair is the map being *in the tree*, not the map existing."""

    def test_the_map_exists(self) -> None:
        assert MAP.is_file(), (
            "docs/COMMIT_HASH_MAP_g11.json is absent. Run "
            "scripts/repair_hist01.py while .git/filter-repo/commit-map still "
            "exists -- it cannot be rebuilt once that is gone")

    def test_the_map_is_tracked_by_git(self) -> None:
        rel = MAP.relative_to(ROOT).as_posix()
        assert git("ls-files", "--error-unmatch", rel) is not None, (
            f"{rel} is untracked. An untracked correction map is in exactly "
            "the position .git/filter-repo/commit-map was in -- one disk, one "
            "copy, no backup -- which is the whole reason it was copied out")

    def test_the_map_records_where_it_came_from(self) -> None:
        doc = load_map() or {}
        rewrite = doc.get("rewrite") or {}
        assert rewrite.get("tool") == "git filter-repo"
        assert rewrite.get("source") == ".git/filter-repo/commit-map"
        assert rewrite.get("when"), (
            "a correction map that does not say when the rewrite happened "
            "cannot be checked against anything")


class TestTheMapVerifiesItself:
    """All three checks the builder runs, recorded as passing."""

    @pytest.mark.parametrize(
        "check", ["V1_existence", "V2_agreement", "V3_chain"])
    def test_each_verification_passes(self, check: str) -> None:
        doc = load_map() or {}
        ver = (doc.get("verification") or {}).get(check) or {}
        assert ver.get("passes") is True, (
            f"{check} is not recorded as passing: {ver.get('failures')}")
        assert ver.get("checked", 0) > 0, (
            f"{check} passes vacuously -- it checked nothing, and a "
            "verification over an empty set is not a verification")

    def test_the_helper_agrees_the_map_is_verified(self) -> None:
        assert map_is_verified()

    def test_nothing_is_unresolved(self) -> None:
        doc = load_map() or {}
        assert doc.get("unresolved") == [], (
            f"the map leaves hashes unresolved: {doc.get('unresolved')}")


class TestTheMapActuallyResolvesWhatItClaims:
    """Re-derived against git, not read back out of the artefact."""

    def test_every_recorded_hash_resolves_to_a_real_commit(self) -> None:
        bad = [(where, h) for where, h in recorded_hashes()
               if not is_real_commit(h)]
        assert not bad, (
            "HIST-01 is not repaired for:\n  "
            + "\n  ".join(f"{w} -> {h}" for w, h in bad))

    def test_the_per_generation_champions_land_on_their_own_generation(
            self) -> None:
        """The independent check: the commit's message names its generation.

        The messages were written before the rewrite; the map came out of
        ``filter-repo``. Two sources, so agreement is evidence.
        """
        mismatches = []
        for path in STATE_FILES:
            doc = json.loads(path.read_text(encoding="utf-8"))
            for gen, recorded in (doc.get("champion_per_generation")
                                  or {}).items():
                target = resolve_commit(recorded)
                if target is None:
                    mismatches.append(f"{path.name}:{gen} does not resolve")
                    continue
                subject = git("log", "--format=%s", "-1", target) or ""
                tag = {"close": "close",
                       "close_addendum": "addendum"}.get(gen, gen)
                if not subject.lower().startswith(tag.lower()):
                    mismatches.append(
                        f"{path.name}:{gen} -> {target[:8]} {subject[:50]!r}")
        assert not mismatches, "\n  ".join(mismatches)


class TestTheResolverFailsClosed:
    """``IA-1``. A plausible negative, and a positive that would fail if the
    rule did nothing."""

    def test_negative_control_a_plausible_absent_hash_does_not_resolve(
            self) -> None:
        """Plausible, not malformed: the right shape, from the right alphabet,
        and simply not a commit here.

        A resolver that answered this would be resolving by *shape* rather than
        by evidence, and every guard leaning on it would be worthless.
        """
        plausible = "d4f1a2b3c4e5f60718293a4b5c6d7e8f90a1b2c3"
        assert git("cat-file", "-t", plausible) != "commit", (
            "the control hash is real in this repository; pick another")
        assert resolve_commit(plausible) is None
        assert not is_real_commit(plausible)

    def test_negative_control_a_rewritten_target_is_not_accepted_backwards(
            self) -> None:
        """The map is directional. A *new* hash must not resolve as an *old*
        one just because it appears in the table."""
        doc = load_map() or {}
        entries = [e for e in doc.get("entries", [])
                   if e.get("route") != "direct"]
        assert entries, "no rewritten entries to test directionality on"
        for entry in entries[:5]:
            assert resolve_commit(entry["resolves"]) == entry["resolves"], (
                "a mapped target must resolve to itself, directly -- it is a "
                "real commit in this tree")

    def test_positive_control_the_map_is_what_makes_them_resolve(self) -> None:
        """Would fail if the rule did nothing.

        If the correction map were inert, these hashes would not resolve --
        which is precisely the state the tree was in for three generations.
        At least one recorded hash must resolve *through the map* rather than
        directly, or the map is not doing anything and this whole repair is
        decoration.
        """
        through_map = [
            h for _, h in recorded_hashes()
            if git("cat-file", "-t", h) != "commit" and is_real_commit(h)]
        assert through_map, (
            "no recorded hash resolves through the map. Either the history was "
            "never rewritten -- in which case this repair is unnecessary and "
            "should be deleted rather than kept as decoration -- or the "
            "resolver is not consulting the map")

    def test_positive_control_the_resolver_refuses_an_unverified_map(
            self, tmp_path, monkeypatch) -> None:
        """The fail-closed path, exercised rather than asserted."""
        import commit_map

        broken = tmp_path / "broken_map.json"
        doc = load_map() or {}
        doc["verification"]["V2_agreement"]["passes"] = False
        broken.write_text(json.dumps(doc), encoding="utf-8")
        monkeypatch.setattr(commit_map, "MAP", broken)
        assert not commit_map.map_is_verified()
        rewritten = [e["recorded"] for e in (load_map() or {}).get("entries", [])
                     if e.get("route") != "direct"]
        assert rewritten, "no rewritten entry to test the refusal on"
        assert commit_map.resolve_commit(rewritten[0]) is None, (
            "the resolver used a map whose own verification failed")


class TestTheFindingIsNotSilentlyDowngraded:
    """A repair that is not recorded as a repair is just a passing test."""

    def test_the_map_says_what_it_does_not_do(self) -> None:
        doc = load_map() or {}
        text = (doc.get("what_it_does_not_do") or "").lower()
        assert "mutation" in text and "supersession" in text, (
            "the map must record that it supersedes rather than mutates the "
            "state files; directive section 6 reserves mutation of a ledger "
            "entry and a repair that quietly edited one would be a violation "
            "wearing a fix's name")

    def test_no_loop_state_file_was_edited_by_the_repair(self) -> None:
        """The state files' recorded hashes are still the *old* ones."""
        doc = load_map() or {}
        rewritten = {e["recorded"] for e in doc.get("entries", [])
                     if e.get("route") != "direct"}
        still_recorded = {h for _, h in recorded_hashes()}
        assert rewritten <= still_recorded, (
            "a hash the map lists as rewritten is no longer recorded in any "
            "state file, which means a state file was edited. Directive "
            "section 6 reserves that")
