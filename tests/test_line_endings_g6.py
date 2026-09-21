"""A checkout must return exactly what was committed — AUDIT_g6 §3.4.

Commit `c115757` adopted this repository byte-for-byte and was attested against
`PRESERVE_MANIFEST_g0.sha256`: 164/164 tracked files identical. That attestation
means nothing if a *checkout* can hand back different bytes than were committed.

It very nearly did. `core.autocrlf` was `true` at system level on the adopting
machine, no `.gitattributes` existed, and 39+ tracked files carry CRLF. Staging
would have rewritten all of them and the attestation would have failed — on a git
configuration default, not on anything wrong with the project. It was caught by
hand and worked around with a repository-local `core.autocrlf=false`.

A local config setting does not travel with a clone. `.gitattributes` makes it
travel; this test is what proves it still works, on whatever machine runs the
suite, under whatever `core.autocrlf` that machine has set.

The index currently holds 119 CRLF files, 74 LF, 2 genuinely mixed, 12 binary and
1 with no line endings at all. That mixture is *what was measured*, and
normalising it would change the bytes the attestation covers. So the policy is
`* -text` — never convert — rather than the more usual `* text=auto`.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> bytes:
    out = subprocess.run(
        ["git", *args], cwd=str(REPO_ROOT), capture_output=True, timeout=120
    )
    assert out.returncode == 0, f"git {' '.join(args)} failed: {out.stderr!r}"
    return out.stdout


def _in_a_checkout() -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"], cwd=str(REPO_ROOT),
            capture_output=True, timeout=30, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _in_a_checkout(), reason="not run from a git checkout"
)


def _tracked_files() -> list:
    raw = _git("ls-files", "-z").decode("utf-8", "replace")
    return [n for n in raw.split("\0") if n]


class TestCheckoutReturnsWhatWasCommitted:
    """The property `.gitattributes` exists to guarantee."""

    def test_unmodified_files_match_their_blob_byte_for_byte(self) -> None:
        """Working-tree bytes == index bytes, for every *unmodified* tracked file.

        This is the comparison run by hand before the adoption commit, where it
        caught the CRLF rewrite. Here it runs on every suite invocation.

        Files git reports as modified are excluded, and that exclusion is the
        whole design of this test rather than a loophole in it. An earlier draft
        compared *all* tracked files and so failed the moment anyone had an
        uncommitted edit — conflating "a checkout returns the committed bytes"
        with "the tree is clean". Only the first is the property `.gitattributes`
        guarantees; the second is not a property of anything. The exclusion is
        derived from `git diff --name-only`, so a file cannot dodge the check by
        being silently rewritten: a line-ending-only rewrite *is* a modification
        and would show up in `test_no_tracked_file_would_be_normalised` below,
        which has no exclusions at all.
        """
        modified = {
            n for n in _git("diff", "--name-only", "-z").decode("utf-8", "replace").split("\0") if n
        }
        mismatches, checked = [], 0
        for name in _tracked_files():
            if name in modified:
                continue
            path = REPO_ROOT / name
            if not path.is_file():
                continue                      # staged deletion; not this test's concern
            checked += 1
            blob = _git("cat-file", "blob", f":{name}")
            disk = path.read_bytes()
            if hashlib.sha256(blob).hexdigest() != hashlib.sha256(disk).hexdigest():
                mismatches.append(
                    f"{name}: blob {len(blob)} B vs working tree {len(disk)} B"
                )
        assert checked > 100, (
            f"only {checked} unmodified tracked files were compared -- if nearly "
            "everything is modified this test is not exercising anything"
        )
        assert not mismatches, (
            "AUDIT_g6 3.4 -- a checkout would not return the committed bytes. "
            "This is the failure mode that nearly broke the c115757 attestation:\n  "
            + "\n  ".join(mismatches[:20])
        )

    def test_gitattributes_disables_conversion(self) -> None:
        """`* -text` must be in force, whatever core.autocrlf says locally."""
        assert (REPO_ROOT / ".gitattributes").is_file(), ".gitattributes is missing"
        # git check-attr reports the effective attribute for a representative
        # text file, so this tests the resolved policy rather than the file text.
        out = _git("check-attr", "text", "--", "README.md").decode("utf-8", "replace")
        assert "text: unset" in out, (
            f"line-ending conversion is not disabled for README.md: {out.strip()!r}. "
            "`* -text` should resolve to `text: unset`."
        )

    def test_no_tracked_file_would_be_normalised(self) -> None:
        """`git ls-files --eol` must report no file whose index and work tree differ.

        Catches the case where `.gitattributes` is present but a rule elsewhere
        re-enables conversion for some path.
        """
        raw = _git("ls-files", "--eol").decode("utf-8", "replace")
        offenders = []
        for line in raw.splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            index_eol, work_eol = parts[0], parts[1]      # e.g. "i/crlf" "w/crlf"
            if index_eol.split("/")[1] != work_eol.split("/")[1]:
                offenders.append(line.strip())
        assert not offenders, (
            "AUDIT_g6 §3.4 -- index and working-tree line endings disagree, so a "
            "fresh checkout would alter these files:\n  " + "\n  ".join(offenders[:20])
        )


class TestTheGuardIsNotVacuous:
    """Controls: a check that inspected nothing would pass silently."""

    def test_there_are_tracked_files_to_check(self) -> None:
        assert len(_tracked_files()) > 100, (
            f"only {len(_tracked_files())} tracked files found -- the sweep above "
            "is not covering the repository"
        )

    def test_the_repository_really_does_contain_crlf_files(self) -> None:
        """If this ever stops being true, the policy above is no longer load-bearing.

        The whole point of `* -text` here is that the tree is *mixed*. A tree that
        became uniformly LF could safely use `text=auto`, and this file should
        then be revisited rather than left in place unexamined.
        """
        raw = _git("ls-files", "--eol").decode("utf-8", "replace")
        crlf = sum(1 for line in raw.splitlines() if line.split()[:1] == ["i/crlf"])
        assert crlf > 0, (
            "no CRLF files remain in the index; revisit .gitattributes and this "
            "test rather than assuming the `* -text` policy is still required"
        )


class TestNoTextIoUsesThePlatformEncoding:
    """BUG-14, made permanent — AUDIT_g6 §3.2a.

    BUG-14 was a Windows-only encoding defect: the notebook generator crashed on
    any non-ASCII physics symbol under a non-UTF-8 default encoding, so it could
    not run at all on Windows. It was fixed file by file. Nothing stopped the next
    one appearing, and the generation-6 portability sweep found one:
    ``tests/test_robustness.py`` read a UTF-8 manifest with the platform encoding.

    Under cp1252 that either raises or, worse, decodes wrongly and compares the
    mangled result — a silent wrong answer on the one CI leg that exists to catch
    exactly this class. This guard removes the file-by-file part.
    """

    def test_every_text_open_declares_utf8(self) -> None:
        import ast

        offenders = []
        for root in ("src", "scripts", "tests"):
            for path in sorted(Path(REPO_ROOT / root).rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    func = node.func
                    name = (func.attr if isinstance(func, ast.Attribute)
                            else getattr(func, "id", None))
                    if name not in ("open", "read_text", "write_text"):
                        continue
                    if any(kw.arg == "encoding" for kw in node.keywords):
                        continue
                    mode = None
                    for arg in node.args[1:2]:
                        if isinstance(arg, ast.Constant):
                            mode = arg.value
                    for kw in node.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                            mode = kw.value.value
                    if mode and "b" in str(mode):
                        continue          # binary mode has no encoding
                    offenders.append(
                        f"{path.relative_to(REPO_ROOT).as_posix()}:{node.lineno} {name}()"
                    )
        assert not offenders, (
            "AUDIT_MASTER BUG-14 class -- text I/O using the platform encoding:\n  "
            + "\n  ".join(offenders)
        )

    def test_the_scan_is_not_vacuous(self) -> None:
        """Control: the walk must find the calls it claims to be checking."""
        import ast

        total = 0
        for root in ("src", "scripts", "tests"):
            for path in sorted(Path(REPO_ROOT / root).rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                total += sum(
                    1 for n in ast.walk(tree)
                    if isinstance(n, ast.Call)
                    and (n.func.attr if isinstance(n.func, ast.Attribute)
                         else getattr(n.func, "id", None)) in ("open", "read_text", "write_text")
                )
        assert total > 20, f"only {total} text-I/O calls found; the scan is not covering the tree"
