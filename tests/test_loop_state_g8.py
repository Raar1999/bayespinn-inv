"""The loop-state file cannot name its own commit, so the schema defines it away.

Generation 7 wrote ``LOOP_STATE_v4.json`` pointing ``champion_commit`` at the
commit that wrote it, which is not a commit that can exist: the file's contents
are part of the tree the commit hashes. Generation 7 then wrote a second commit
to repair the pointer, and the state file's own history records the loop.

The generation-8 ruling closes it by definition rather than by cleverness:

    ``champion`` means **the last content commit**, by definition, documented in
    the schema, with ``bookkeeping_commit`` left null at write time. Add a test
    asserting ``champion`` is never the commit that wrote the file.

That last sentence is the exact invariant, and it is exactly checkable:
``git log -1 -- LOOP_STATE_v5.json`` is the commit that produced the file's
current bytes, and ``champion_commit`` must not be it.

What this test deliberately does **not** assert
-----------------------------------------------
That the champion never touches *a* loop-state file. It sometimes does --
``922c2cc``, generation 7's champion, modified ``LOOP_STATE_v4.json`` to record a
finding, and ``7ef48c4`` later wrote the pointer. Both are correct. The fixed
point is only about *the commit whose tree contains the pointer*, and widening
the assertion past that would fail on correct history, which is how guards get
disabled.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from commit_map import is_real_commit, resolution_note, resolve_commit

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "LOOP_STATE_v5.json"


def git(*args):
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                         text=True, timeout=30)
    return out.stdout.strip() if out.returncode == 0 else None


@pytest.fixture(scope="module")
def state():
    return json.loads(STATE.read_text(encoding="utf-8"))


class TestTheFixedPointIsDefinedAway:

    def test_the_schema_documents_what_champion_means(self, state):
        """A definition that lives only in a ruling is the OPS-01 defect again."""
        schema = state["schema"]
        assert "champion_commit" in schema
        text = schema["champion_commit"].lower()
        assert "content commit" in text
        assert "never the commit that wrote this file" in text
        assert "bookkeeping_commit" in schema
        assert "null" in schema["bookkeeping_commit"].lower()

    def test_champion_is_not_the_commit_that_wrote_this_file(self, state):
        """The invariant, stated exactly.

        ``git log -1`` on the path gives the commit that produced the file's
        current bytes. If the champion pointer were that commit, the pointer
        would have had to know its own tree's hash before the tree existed.
        """
        writer = git("log", "-1", "--format=%H", "--", str(STATE.name))
        if not writer:
            pytest.skip("no git history for the state file in this checkout")
        assert state["champion_commit"] != writer, (
            f"champion_commit points at {writer[:8]}, which is the commit that "
            "wrote this file. That is the fixed point generation 7 walked into: "
            "a state file cannot name its own commit. Point it at the last "
            "content commit instead.")

    def test_bookkeeping_commit_is_null_at_write_time(self, state):
        """The other half of the definition, and the reason the loop closes.

        Nothing may fill this in during the commit that writes the file, because
        the value would be that commit's own hash. A later generation reading git
        history may fill it; this generation may not, and the null is the record
        that it did not.
        """
        assert state["bookkeeping_commit"] is None

    def test_the_champion_is_a_real_reachable_commit(self, state):
        head = git("rev-parse", "HEAD")
        if head is None:
            pytest.skip("not a git checkout")
        champ = state["champion_commit"]
        resolved = resolve_commit(champ)
        assert resolved is not None, resolution_note(champ)
        merge_base = git("merge-base", "--is-ancestor", resolved, "HEAD")
        assert merge_base is not None, (
            f"champion_commit {champ[:8]} resolves to {resolved[:8]}, which is "
            "not an ancestor of HEAD")

    def test_the_champion_carries_content(self, state):
        """"Last *content* commit" is a claim about what it changed."""
        champ = state["champion_commit"]
        files = git("show", "--name-only", "--format=",
                    resolve_commit(champ) or champ)
        if files is None:
            pytest.skip("champion commit not available")
        touched = [f for f in files.splitlines() if f.strip()]
        assert touched, f"{champ[:8]} changed nothing"
        content = [f for f in touched
                   if not f.startswith("LOOP_STATE_")]
        assert content, (
            f"{champ[:8]} changed only loop-state files, so it is a bookkeeping "
            "commit, not a content commit")


class TestTheStateFileIsInternallyConsistent:

    def test_the_per_generation_champions_are_all_real(self, state):
        for gen, commit in state["champion_per_generation"].items():
            assert is_real_commit(commit), f"{gen}: {resolution_note(commit)}"

    def test_this_generations_champion_matches_the_pointer(self, state):
        gen = str(state["generation"])
        per = state["champion_per_generation"][f"g{gen}"]
        assert state["champion_commit"].startswith(per) or \
            per.startswith(state["champion_commit"][:len(per)]), (
                f"champion_commit and champion_per_generation.g{gen} disagree")

    def test_every_open_finding_has_a_severity_and_a_status(self, state):
        for f in state["open_findings"]:
            assert f.get("id"), f
            assert f.get("severity"), f["id"]
            assert f.get("status"), f["id"]

    def test_a_permanently_accepted_finding_owes_a_cost_statement(self, state):
        """The mislabel is what corrupts a status system, not the open finding."""
        for f in state["open_findings"]:
            if "ACCEPTED-PERMANENT" in f["status"]:
                assert f.get("cost_statement"), (
                    f"{f['id']} is ACCEPTED-PERMANENT with no cost statement")

    def test_the_not_to_be_written_list_survives(self, state):
        """A withheld number stays withheld until something measures it."""
        forbidden = state["not_supported_and_not_to_be_written"]
        joined = " ".join(forbidden).lower()
        assert "rank fraction" in joined
        assert "frequency" in joined or "probability" in joined
        assert "contraction" in joined
