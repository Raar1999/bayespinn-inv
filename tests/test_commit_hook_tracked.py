"""The ``commit-msg`` hook is tracked in this tree, and it does what it claims.

Why this module exists
----------------------
The hook that strips AI-attribution trailers from commit messages was installed
on 2026-08-28 at ``~/.git-hooks``, selected by a **machine-global**
``core.hooksPath``. That location is outside the repository, outside the bundle,
and outside the ``E:`` copy. A clone of this tree on another machine therefore
inherited none of the protection, and nothing in the tree said so.

Generation 12 recorded the hook as ``tested_not_assumed`` with "both controls"
in ``LOOP_STATE_v11.json``. The verification behind that phrase was ad hoc and
left no artefact: no test module named it, so nothing re-ran it and nothing
would notice it breaking. That is the ``SW-20`` failure mode one level up --
not a guard that cannot fire, but a guard that exists only in a status claim.
``scripts/hooks/commit-msg`` and this module are that claim's missing evidence.

What is asserted, and what is deliberately not
----------------------------------------------
The subject here is a **shell script**, so ``SW-20``'s AST clause has no
purchase -- there is no Python AST for bash. Its *purpose* does apply, and both
controls are implemented by executing the tracked script:

* **positive control** -- a message carrying a planted
  ``Co-Authored-By: Claude <noreply@anthropic.com>`` trailer comes back with
  that line gone and every substantive line intact, in order;
* **negative control** -- an ordinary message, including one whose prose names
  the concepts the hook hunts for without matching a pattern, comes back
  **byte-identical**.

The hook is run as a subprocess against a temporary file. This module never
reads ``core.hooksPath`` and never consults the machine's git configuration:
the property under test is that *the script committed here* behaves correctly,
which is what a cloner gets. Whether this particular machine happens to have it
activated is a separate question, and one a clone cannot inherit the answer to.

Activation for a cloner is one command, recorded in ``README.md``::

    git config core.hooksPath scripts/hooks

See ``docs/RULES_ENACTED.md`` for ``SW-20``.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

#: The tracked hook. The path is also the activation target in README.md; if it
#: moves, that instruction goes stale and this assertion is what says so.
HOOK = REPO / "scripts" / "hooks" / "commit-msg"

#: The trailer this repository exists to keep out of its history. Written as a
#: whole line because that is the unit the hook removes.
PLANTED_TRAILER = "Co-Authored-By: Claude <noreply@anthropic.com>"


def _bash() -> str:
    """Locate ``bash``, or fail loudly.

    Deliberately **not** a skip. ``HIST-01`` is the standing lesson here: the
    ``DOC-07`` guard turned itself into a skip when its commit hashes stopped
    resolving, ran over an empty range for four generations, and a green suite
    reported nothing. A guard that quietly does not run is worse than absent,
    because absence is visible. Both CI legs -- ubuntu-latest and
    windows-latest, the latter via Git for Windows -- provide bash.
    """
    found = shutil.which("bash")
    if found is None:
        pytest.fail(
            "bash is not on PATH, so the tracked commit-msg hook cannot be "
            "executed and its behaviour is unverified. This is a failure, not "
            "a skip: an unrunnable guard must be visible."
        )
    return found


def _run_hook(message: str, tmp_path: Path) -> str:
    """Run the tracked hook over ``message``; return the file's contents after.

    Mirrors how git invokes it: the message is written to a file whose path is
    the hook's sole argument, and the hook edits that file in place.

    All file I/O here is **binary**. Python's text mode would translate line
    endings on Windows in both directions, which is exactly the difference the
    negative control is trying to detect; the caller compares the returned
    string to what it wrote, so any rewriting the hook does must survive the
    round trip visibly rather than be normalised away by the harness.
    """
    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_bytes(message.encode("utf-8"))

    proc = subprocess.run(
        [_bash(), str(HOOK), str(msg_file)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=60,
    )
    assert proc.returncode == 0, (
        f"the hook exited {proc.returncode}; git would abort the commit.\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    return msg_file.read_bytes().decode("utf-8")


# --------------------------------------------------------------------------
# The hook is present in the tree at all
# --------------------------------------------------------------------------

def test_hook_is_tracked_and_non_empty() -> None:
    """The file exists, carries content, and git knows about it.

    ``git ls-files`` rather than ``Path.exists`` alone: an untracked file in a
    working tree is exactly the situation this task exists to end. A cloner
    gets tracked files and nothing else.
    """
    assert HOOK.is_file(), f"{HOOK.relative_to(REPO)} is missing"
    assert HOOK.stat().st_size > 0, f"{HOOK.relative_to(REPO)} is empty"

    listed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "scripts/hooks/commit-msg"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert listed.returncode == 0, (
        "scripts/hooks/commit-msg is not tracked by git, so a clone would not "
        "receive it -- which is the whole defect this file addresses"
    )


def test_readme_records_how_to_activate_the_hook() -> None:
    """A tracked hook nobody knows to switch on protects nobody.

    ``core.hooksPath`` is not set by cloning; it is a per-clone configuration
    step. The instruction has to travel in the tree with the script.
    """
    readme = (REPO / "README.md").read_text(encoding="utf-8", errors="replace")
    assert "git config core.hooksPath scripts/hooks" in readme, (
        "README.md must carry the activation command verbatim; without it the "
        "tracked hook is inert on every fresh clone"
    )


# --------------------------------------------------------------------------
# Positive control -- the guard must fire
# --------------------------------------------------------------------------

def test_planted_trailer_is_stripped(tmp_path: Path) -> None:
    """A planted attribution trailer is removed; the real message survives.

    Both halves matter. A hook that emptied the file would pass a
    "trailer is gone" assertion and destroy every commit message in the
    repository, so the surviving lines are asserted explicitly and in order.
    """
    body = [
        "g13: track the commit-msg hook in the tree",
        "",
        "The hook lived only at a machine-global core.hooksPath, so a clone",
        "on another machine inherited no protection at all.",
    ]
    message = "\n".join([*body, "", PLANTED_TRAILER, ""])

    assert PLANTED_TRAILER in message, "the plant must be present before the run"

    result = _run_hook(message, tmp_path)

    assert PLANTED_TRAILER not in result, (
        "the hook left the planted trailer in place -- it is not firing"
    )
    assert "Co-Authored-By" not in result

    surviving = [line for line in result.splitlines() if line.strip()]
    expected = [line for line in body if line.strip()]
    assert surviving == expected, (
        "the hook removed more than the trailer.\n"
        f"expected substantive lines: {expected}\ngot: {surviving}"
    )


@pytest.mark.parametrize(
    "trailer",
    [
        "Co-Authored-By: Claude <noreply@anthropic.com>",
        "Co-authored-by: claude <noreply@anthropic.com>",
        "Co-Authored-By: Claude Opus <noreply@anthropic.com>",
        "Generated with Claude Code",
        "Generated by AI",
    ],
    ids=["canonical", "lowercase", "named-model", "generated-with", "generated-by"],
)
def test_attribution_shapes_are_stripped(trailer: str, tmp_path: Path) -> None:
    """The variants the global rules forbid, not just the canonical one.

    Case folding is the interesting case: git's own trailer convention is
    ``Co-authored-by``, and a guard matching only the capitalised spelling
    would pass its author's test and miss what git actually writes.
    """
    subject = "g13: a change with an unwanted trailer"
    result = _run_hook(f"{subject}\n\n{trailer}\n", tmp_path)

    assert trailer not in result, f"the hook did not strip {trailer!r}"
    assert subject in result, "the subject line must survive"


# --------------------------------------------------------------------------
# Negative control -- the guard must not fire
# --------------------------------------------------------------------------

def test_ordinary_message_is_byte_identical(tmp_path: Path) -> None:
    """An ordinary message comes back unchanged, byte for byte.

    Byte-identity, not equality after normalisation. ``.gitattributes`` pins
    every file in this tree to ``-text`` precisely so that committed bytes are
    the bytes that were attested; a hook that silently rewrote line endings or
    appended a newline would be corrupting messages on every commit while
    passing a looser check.
    """
    message = (
        "g13: track the commit-msg hook and give it a guard\n"
        "\n"
        "The hook was installed at a machine-global core.hooksPath ten minutes\n"
        "before the history rewrite. It is now tracked at scripts/hooks so a\n"
        "clone receives it, and tests/test_commit_hook_tracked.py runs it.\n"
        "\n"
        "Counts and digests are in the manifest, not here.\n"
    )

    assert _run_hook(message, tmp_path) == message, (
        "the hook modified an ordinary commit message"
    )


def test_prose_about_attribution_is_not_mangled(tmp_path: Path) -> None:
    """Prose describing what the hook forbids must survive it.

    ``SW-20``'s negative control, applied to a text filter. The words
    "generated", "co-author" and "assisted" all appear here, near each other,
    in a message whose subject is the hook itself -- the exact commit most
    likely to trip a lazily-written pattern. None of these lines matches a
    pattern the hook carries, and the file must come back untouched.
    """
    message = (
        "g13: record why the attribution filter exists\n"
        "\n"
        "The rule forbids naming a co-author that did not write the change,\n"
        "and forbids claiming a file was generated somewhere other than in\n"
        "this tree. A reviewer assisted by tooling is still the author.\n"
        "\n"
        "The filter removes whole lines, so prose stating the rule has to be\n"
        "shown to survive it. This message is that demonstration.\n"
    )

    assert _run_hook(message, tmp_path) == message, (
        "the hook fired on prose describing the rule rather than on a "
        "violation of it -- the SW-20 failure mode"
    )


def test_empty_and_comment_only_messages_survive(tmp_path: Path) -> None:
    """An aborted commit must not be turned into a non-empty one.

    Git treats a message that is empty once comments are stripped as
    "abort the commit". A hook that wrote a stray newline into such a file
    would convert a deliberate abort into a commit with a blank message.
    """
    message = "\n# Please enter the commit message for your changes.\n#\n"
    assert _run_hook(message, tmp_path) == message, (
        "the hook rewrote a comment-only message, which git reads as an abort"
    )
