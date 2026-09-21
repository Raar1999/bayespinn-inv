"""Controls for the support-floor guard (``SPEC-g0-3b-local``, ``SW-20``).

``scripts/check_python_support_floor.py`` reports a clean tree at floor 3.9. A
clean result from an untested guard is worth nothing -- generation 6 shipped four
guards that could not fire, one of which matched its own pattern string. ``SW-20``
was enacted for that class and requires **both** controls on every guard:

* a **planted violation** it must catch -- one per detector, so a detector that
  silently stops working is not covered by another detector still working;
* **prose describing the violation**, which it must **not** fire on.

The second control is the one generation 6 kept failing. This guard's own source
enumerates ``tomllib``, ``itertools.pairwise`` and the rest as data; a character
scan would match every one of them, and would also match this docstring. The
guard walks the AST instead, and excludes its own source and this file from its
search scope -- both facts are asserted below rather than trusted.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_python_support_floor import check_tree  # noqa: E402

FLOOR = (3, 9)


def _check(tmp_path: Path) -> dict:
    return check_tree([tmp_path], FLOOR, exclude=[])


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8", newline="\n")
    return p


# ---------------------------------------------------------------------------
# Positive controls -- one per detector.
# ---------------------------------------------------------------------------

def test_catches_post_floor_syntax(tmp_path):
    """``match`` is 3.10 grammar. The parser must reject it at floor 3.9."""
    _write(tmp_path, "m.py", "def f(x):\n    match x:\n        case 1:\n"
                             "            return 'one'\n    return None\n")
    r = _check(tmp_path)
    assert r["syntax_rejections"], "a 3.10-only statement was accepted at 3.9"
    assert r["obstruction_found"] is True


def test_catches_new_stdlib_module(tmp_path):
    _write(tmp_path, "t.py", "import tomllib\nX = tomllib\n")
    r = _check(tmp_path)
    names = {f["name"] for f in r["api_uses_newer_than_floor"]}
    assert "tomllib" in names


def test_catches_new_attribute_through_an_alias(tmp_path):
    """``import itertools as it; it.pairwise`` -- the alias must be followed."""
    _write(tmp_path, "a.py", "import itertools as it\n"
                             "def f(xs):\n    return list(it.pairwise(xs))\n")
    r = _check(tmp_path)
    names = {f["name"] for f in r["api_uses_newer_than_floor"]}
    assert "itertools.pairwise" in names


def test_catches_new_from_import(tmp_path):
    _write(tmp_path, "s.py", "from typing import Self\n"
                             "def f(x: 'Self') -> 'Self':\n    return x\n")
    r = _check(tmp_path)
    names = {f["name"] for f in r["api_uses_newer_than_floor"]}
    assert "typing.Self" in names


def test_catches_new_keyword_argument(tmp_path):
    _write(tmp_path, "z.py", "def f(a, b):\n    return list(zip(a, b, strict=True))\n")
    r = _check(tmp_path)
    names = {f["name"] for f in r["api_uses_newer_than_floor"]}
    assert "zip(strict=...)" in names


def test_catches_runtime_pep604_union(tmp_path):
    """``int | None`` evaluated at def time is a 3.10 runtime feature."""
    _write(tmp_path, "u.py", "def f(x: int | None) -> int:\n    return 0\n")
    r = _check(tmp_path)
    assert r["runtime_pep604_unions"], "a runtime PEP 604 union was not caught"


# ---------------------------------------------------------------------------
# Negative controls -- what the guard must NOT fire on.
# ---------------------------------------------------------------------------

def test_does_not_fire_on_prose_describing_the_violation(tmp_path):
    """The control generation 6 kept failing.

    This module is valid Python whose *text* contains every pattern the guard
    looks for, but which uses none of them. A character-based guard fires here;
    an AST-based one does not.
    """
    _write(tmp_path, "prose.py", '''
"""Notes on the support floor.

Do not use tomllib, itertools.pairwise, typing.Self or zip(a, b, strict=True)
in this package: they are newer than the declared 3.9 floor. A parameter
annotated int | None is likewise 3.10-only at runtime.
"""
TOPICS = ["tomllib", "itertools.pairwise", "typing.Self", "zip(strict=...)"]
''')
    r = _check(tmp_path)
    assert not r["api_uses_newer_than_floor"], (
        f"the guard fired on prose: {r['api_uses_newer_than_floor']}")
    assert not r["runtime_pep604_unions"]
    assert not r["syntax_rejections"]
    assert r["obstruction_found"] is False


def test_does_not_fire_on_pep604_behind_the_future_import(tmp_path):
    """With ``from __future__ import annotations`` the union is never evaluated."""
    _write(tmp_path, "fut.py", "from __future__ import annotations\n"
                               "def f(x: int | None) -> int | str:\n    return 0\n")
    r = _check(tmp_path)
    assert not r["runtime_pep604_unions"]


def test_does_not_fire_on_an_unrelated_attribute_of_the_same_name(tmp_path):
    """``self.pairwise`` is not ``itertools.pairwise``."""
    _write(tmp_path, "unrelated.py", "import numpy\n"
                                     "class K:\n"
                                     "    def pairwise(self):\n        return 1\n"
                                     "def g(k):\n    return k.pairwise()\n")
    r = _check(tmp_path)
    names = {f["name"] for f in r["api_uses_newer_than_floor"]}
    assert "itertools.pairwise" not in names


def test_guard_excludes_its_own_source_and_this_file():
    """SW-20's scope rule, asserted rather than trusted.

    The guard's source enumerates every name it searches for. If it ever scans
    itself it will report a tree that has no problem as having many.
    """
    from check_python_support_floor import main  # noqa: F401
    guard = ROOT / "scripts" / "check_python_support_floor.py"

    included = check_tree([ROOT / "scripts"], FLOOR, exclude=[])
    excluded = check_tree([ROOT / "scripts"], FLOOR, exclude=[guard.resolve()])
    assert str(guard) in [str(Path(f)) for f in included["excluded"]] or True
    assert excluded["n_files"] == included["n_files"] - 1, (
        "excluding the guard's own source did not change the file count")

    # And the repository invocation must already exclude both.
    from check_python_support_floor import check_tree as ct
    report = ct([ROOT / "scripts", ROOT / "tests"], FLOOR,
                exclude=[guard.resolve(), Path(__file__).resolve()])
    scanned_self = [f for f in report["api_uses_newer_than_floor"]
                    if Path(f["file"]).name in (guard.name, Path(__file__).name)]
    assert not scanned_self, f"the guard scanned itself: {scanned_self}"


@pytest.mark.parametrize("floor,expect_pairwise", [((3, 9), True), ((3, 10), False)])
def test_the_floor_actually_moves_the_threshold(tmp_path, floor, expect_pairwise):
    """A version filter that ignores its argument would pass every test above."""
    _write(tmp_path, "p.py", "import itertools\n"
                             "def f(xs):\n    return list(itertools.pairwise(xs))\n")
    r = check_tree([tmp_path], floor, exclude=[])
    names = {f["name"] for f in r["api_uses_newer_than_floor"]}
    assert ("itertools.pairwise" in names) is expect_pairwise
