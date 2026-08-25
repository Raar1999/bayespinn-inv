"""Regression tests for AUDIT_g0 PROV-02.

``git_is_dirty()`` ran ``git status --porcelain --untracked-files=no``, so it was
structurally blind to untracked files. At generation 0 this repository carried 33
untracked paths -- 6 source modules, 8 test files holding 204 of 246 collected
tests, 7 experiment launchers, the CI workflow and the whole audit corpus -- and
the flag could not distinguish that from a fixed typo.

A manifest whose provenance fields cannot tell "one line changed" from "a different
solver, and 83% of the test suite, are missing from this commit" is not a
provenance record. These tests pin the three properties that make it one:

1. an untracked source file makes the tree dirty;
2. tracked-modified and untracked counts are reported separately, so a reader can
   see *which kind* of divergence occurred;
3. a content digest over the tree changes when untracked content changes, so two
   runs claiming the same commit can be told apart.

Every test builds its own throwaway git repository. None of them depends on the
state of the repository under audit.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from bayespinn_inv.utils import provenance
from bayespinn_inv.utils.provenance import (
    RunManifest,
    environment_info,
    git_is_dirty,
    git_status_counts,
    git_tree_digest,
)


def _run(repo: Path, *args: str) -> str:
    """Run a git command inside ``repo`` and return its stdout."""
    out = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, timeout=30
    )
    assert out.returncode == 0, f"git {' '.join(args)} failed: {out.stderr}"
    return out.stdout


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A throwaway git repository with one committed file and no divergence."""
    r = tmp_path / "repo"
    r.mkdir()
    _run(r, "init", "-q")
    _run(r, "config", "user.email", "test@example.invalid")
    _run(r, "config", "user.name", "test")
    _run(r, "config", "core.autocrlf", "false")
    (r / "tracked.py").write_text("x = 1\n", encoding="utf-8")
    _run(r, "add", "-A")
    _run(r, "commit", "-q", "-m", "initial")
    return r


class TestDirtyDetectionSeesUntrackedFiles:
    """PROV-02: the whole point is that an absent-from-git file counts."""

    def test_clean_repo_is_clean(self, repo: Path) -> None:
        assert git_is_dirty(repo=repo) is False

    def test_tracked_modification_is_dirty(self, repo: Path) -> None:
        (repo / "tracked.py").write_text("x = 2\n", encoding="utf-8")
        assert git_is_dirty(repo=repo) is True

    def test_untracked_source_file_is_dirty(self, repo: Path) -> None:
        """The generation-0 defect, in one assertion."""
        (repo / "identifiability.py").write_text("y = 2\n", encoding="utf-8")
        assert git_is_dirty(repo=repo) is True, (
            "AUDIT_g0 PROV-02 -- an untracked source file leaves the tree "
            "unreproducible from the commit, so the tree is dirty"
        )

    def test_ignored_file_is_not_dirty(self, repo: Path) -> None:
        """Ignored build output is not divergence; it must not raise a false alarm."""
        (repo / ".gitignore").write_text("junk/\n", encoding="utf-8")
        _run(repo, "add", "-A")
        _run(repo, "commit", "-q", "-m", "ignore junk")
        (repo / "junk").mkdir()
        (repo / "junk" / "artifact.bin").write_bytes(b"\x00" * 16)
        assert git_is_dirty(repo=repo) is False

    def test_outside_a_checkout_returns_none(self, tmp_path: Path) -> None:
        assert git_is_dirty(repo=tmp_path / "not-a-repo") is None


class TestStatusCountsSeparateTheTwoKinds:
    """A single boolean cannot distinguish a typo from a missing solver."""

    def test_clean_counts_are_zero(self, repo: Path) -> None:
        assert git_status_counts(repo=repo) == {"tracked_modified": 0, "untracked": 0}

    def test_counts_are_reported_separately(self, repo: Path) -> None:
        (repo / "tracked.py").write_text("x = 3\n", encoding="utf-8")
        (repo / "a.py").write_text("a = 1\n", encoding="utf-8")
        (repo / "b.py").write_text("b = 1\n", encoding="utf-8")
        assert git_status_counts(repo=repo) == {"tracked_modified": 1, "untracked": 2}

    def test_outside_a_checkout_returns_none(self, tmp_path: Path) -> None:
        assert git_status_counts(repo=tmp_path / "not-a-repo") is None


class TestTreeDigestDistinguishesContent:
    """Two runs naming the same commit must be distinguishable when they differ."""

    def test_digest_is_stable_for_unchanged_content(self, repo: Path) -> None:
        assert git_tree_digest(repo=repo) == git_tree_digest(repo=repo)

    def test_digest_changes_when_untracked_content_is_added(self, repo: Path) -> None:
        before = git_tree_digest(repo=repo)
        (repo / "new_module.py").write_text("z = 1\n", encoding="utf-8")
        assert git_tree_digest(repo=repo) != before

    def test_digest_changes_when_tracked_content_changes(self, repo: Path) -> None:
        before = git_tree_digest(repo=repo)
        (repo / "tracked.py").write_text("x = 99\n", encoding="utf-8")
        assert git_tree_digest(repo=repo) != before

    def test_digest_ignores_ignored_files(self, repo: Path) -> None:
        (repo / ".gitignore").write_text("junk/\n", encoding="utf-8")
        _run(repo, "add", "-A")
        _run(repo, "commit", "-q", "-m", "ignore junk")
        before = git_tree_digest(repo=repo)
        (repo / "junk").mkdir()
        (repo / "junk" / "artifact.bin").write_bytes(b"\x01" * 32)
        assert git_tree_digest(repo=repo) == before

    def test_outside_a_checkout_returns_none(self, tmp_path: Path) -> None:
        assert git_tree_digest(repo=tmp_path / "not-a-repo") is None


class TestManifestCarriesTheNewFields:
    """SW-13: the manifest is the artefact a reader checks, so it must carry them."""

    def test_manifest_git_block_has_all_four_fields(self, tmp_path: Path) -> None:
        man = RunManifest.create("unit-test", config={"a": 1}, seed=0)
        payload = man.to_dict()["git"]
        for key in ("commit", "dirty", "tracked_modified", "untracked", "tree_digest"):
            assert key in payload, f"manifest git block is missing {key!r}"

    def test_written_manifest_round_trips(self, tmp_path: Path) -> None:
        man = RunManifest.create("unit-test", config={"a": 1}, seed=0)
        path = man.write(tmp_path / "out")
        payload = json.loads(path.read_text(encoding="utf-8"))["git"]
        assert set(payload) >= {
            "commit",
            "dirty",
            "tracked_modified",
            "untracked",
            "tree_digest",
        }

    def test_manifest_reports_this_repository_honestly(self, tmp_path: Path) -> None:
        """Whatever this tree's state is, the boolean and the counts must agree."""
        payload = RunManifest.create("unit-test").to_dict()["git"]
        if payload["dirty"] is None:
            pytest.skip("not run from a git checkout")
        divergent = bool(payload["tracked_modified"]) or bool(payload["untracked"])
        assert payload["dirty"] == divergent, (
            "dirty flag disagrees with its own counts: "
            f"dirty={payload['dirty']} tracked_modified={payload['tracked_modified']} "
            f"untracked={payload['untracked']}"
        )


# ---------------------------------------------------------------------------
# AUDIT_g0 SW-04a -- `except Exception: pass` in library code.
# ---------------------------------------------------------------------------

class TestEnvironmentProbeFailsLoudly:
    """SW-04: no bare except, and no `except Exception: pass`, in library code.

    `environment_info()` swallowed every failure of the CUDA probe, so the
    `cuda_*` keys simply vanished from the manifest. A reader then could not tell
    "this run had no GPU" from "the probe raised" -- the same ambiguity PROV-02
    was about, in miniature: an absent field that could mean two different things.
    """

    def test_no_except_pass_in_the_provenance_module(self) -> None:
        import ast

        source = Path(provenance.__file__).read_text(encoding="utf-8")
        offenders = []
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if all(isinstance(stmt, ast.Pass) for stmt in node.body):
                offenders.append(node.lineno)
            if node.type is None:
                offenders.append(node.lineno)      # bare `except:`
        assert not offenders, (
            f"AUDIT_g0 SW-04a -- silent or bare exception handler at lines {offenders}"
        )

    def test_the_cuda_keys_are_always_present(self) -> None:
        """Absent-vs-unknown must not be ambiguous."""
        info = environment_info()
        for key in ("cuda_available", "cuda_device", "torch_threads"):
            assert key in info, f"{key} missing from environment_info()"

    def test_a_missing_library_is_recorded_as_None_not_omitted(self) -> None:
        info = environment_info()
        for mod in ("numpy", "scipy", "torch", "sklearn", "matplotlib"):
            assert mod in info, f"{mod} missing from environment_info()"
