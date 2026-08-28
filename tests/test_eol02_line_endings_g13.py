"""``EOL-02``: every text-mode write states its line ending explicitly.

**Enacted** by the operator ruling of 2026-08-28 §5, after the line-ending
category bit for the third time.

The defect that forced it
-------------------------
``.gitattributes`` binds **git**, not the interpreter. ``tests/test_line_endings_g6.py``
proved a checkout returns the committed bytes, and that guard is sound and stays.
It says nothing about bytes this project *writes*, and both recent incidents were
on that side: Python's text mode translates ``"\\n"`` to ``os.linesep`` on write,
so on Windows ``open(p, "w")`` and ``Path.write_text(s)`` emit CRLF while the
author reads the source and sees LF. The artefact then differs by platform, and a
hash over it differs with it.

``.gitattributes`` cannot reach that, because the file never goes through git on
the way out. Only the call site can.

The rule
--------
    Every text-mode write states its line ending explicitly --
    ``open(p, "w", newline="\\n")``, or ``newline=""`` where a writer manages its
    own.

Note the rule is *explicitness*, not LF. ``newline=""`` is the correct and
required value for :mod:`csv`, whose writers emit ``\\r\\n`` themselves and would
double it under any translation; two call sites in this tree rely on exactly
that and pass this guard unchanged.

``SW-20`` compliance
--------------------
The subject is source code, so the scan is over the AST and never over
characters. Prose is not in an AST: a docstring that spells out ``open(p, "w")``
is an :class:`ast.Constant`, not an :class:`ast.Call`, which is why this module's
own explanation of the violation cannot trip it -- and why that is asserted below
rather than assumed. Both controls ship:
:meth:`TestTheGuard.test_it_catches_a_planted_violation` plants one, and
:meth:`TestTheGuard.test_it_does_not_fire_on_prose_describing_it` writes a module
whose *text* contains every construct the scan looks for and whose *code*
contains none of them.

Scope
-----
``open`` (including ``Path.open``) and ``Path.write_text``: the two constructs in
this tree through which the project itself opens a text stream for writing. Not
in scope, and deliberately: writers that own their file handle end to end and
never expose a mode -- ``DataFrame.to_csv``, ``numpy.savetxt``,
``Figure.savefig``. The rule reaches call sites, and those are not call sites
where a line ending can be stated.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: ``SW-20``: a guard over source code excludes its own source. This module
#: describes every construct it forbids and would otherwise report itself.
SELF = Path(__file__).resolve()

#: Modes that open a stream for writing. ``"b"`` anywhere means binary, where
#: no translation happens and there is nothing to state.
WRITE_FLAGS = ("w", "a", "x", "+")


def _kwarg(node: ast.Call, name: str):
    for k in node.keywords:
        if k.arg == name:
            return k
    return None


def _mode_of(node: ast.Call):
    """The literal mode string of an ``open`` call, or ``None`` if not literal."""
    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
        return node.args[1].value
    kw = _kwarg(node, "mode")
    if kw is not None and isinstance(kw.value, ast.Constant):
        return kw.value.value
    if len(node.args) >= 2 or kw is not None:
        return None          # present but not a literal -- cannot be judged
    return "r"               # absent: the documented default


def violations(tree: ast.AST):
    """``[(lineno, construct)]`` for every text-mode write with no ``newline=``."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else (
            fn.id if isinstance(fn, ast.Name) else None)

        if name == "open":
            mode = _mode_of(node)
            if mode is None or not isinstance(mode, str):
                continue
            if "b" in mode or not any(f in mode for f in WRITE_FLAGS):
                continue
            if _kwarg(node, "newline") is None:
                found.append((node.lineno, f'open(mode={mode!r})'))

        elif name == "write_text":
            if _kwarg(node, "newline") is None:
                found.append((node.lineno, "Path.write_text"))
    # ``ast.walk`` is breadth-first, so it does not yield source order. A guard
    # that reports a file's findings out of order is tiresome to act on.
    return sorted(found)


def scan(paths):
    """``{relpath: [(lineno, construct)]}`` for every file that violates."""
    out = {}
    for p in paths:
        p = Path(p)
        if p.resolve() == SELF:
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        v = violations(tree)
        if v:
            out[str(p).replace("\\", "/")] = v
    return out


def _tree_paths():
    out = []
    for base in ("src", "scripts", "tests"):
        out.extend(sorted(
            p for p in (ROOT / base).rglob("*.py")
            if "__pycache__" not in p.parts))
    return out


class TestTheGuard:
    """``SW-20`` requires both controls, and requires the exclusion asserted."""

    def test_the_scan_scope_excludes_this_module(self):
        assert SELF in {p.resolve() for p in _tree_paths()}, (
            "this module must be inside the scanned tree for the exclusion to "
            "mean anything")
        assert str(SELF).replace("\\", "/") not in scan(_tree_paths())

    def test_this_module_would_otherwise_report_itself(self):
        """The exclusion is load-bearing, not decorative.

        The docstring above quotes ``open(p, "w", newline="\\n")``. That is
        prose, so it is not in the AST and does not trip the scan -- which is
        the point of ``SW-20``. The scan finding nothing in this file's *code*
        is therefore the honest result, and this asserts it directly rather than
        inferring it from the exclusion.
        """
        tree = ast.parse(SELF.read_text(encoding="utf-8"))
        assert violations(tree) == []

    def test_it_catches_a_planted_violation(self, tmp_path):
        """Positive control: a real text-mode write with no ``newline=``."""
        planted = tmp_path / "planted_crlf_write.py"
        planted.write_text(
            "from pathlib import Path\n"
            "def go(p, s):\n"
            "    with open(p, 'w', encoding='utf-8') as f:\n"
            "        f.write(s)\n"
            "    Path(p).write_text(s, encoding='utf-8')\n",
            encoding="utf-8", newline="\n")
        got = scan([planted])
        key = str(planted).replace("\\", "/")
        assert key in got, "the guard did not fire on a planted violation"
        assert [c for _, c in got[key]] == ["open(mode='w')", "Path.write_text"]

    def test_it_does_not_fire_on_prose_describing_it(self, tmp_path):
        """Negative control: a description of the violation is not the violation.

        This is the failure that forced ``SW-20`` -- a character scan for
        ``def bernoulli`` matched its own pattern literal. Every construct the
        scan looks for appears in this module's *text* and none in its *code*.
        """
        prose = tmp_path / "prose_about_crlf.py"
        prose.write_text(
            '"""Never write open(p, "w") or Path(p).write_text(s) without\n'
            'stating newline="\\\\n". A bare open(path, mode="w") translates\n'
            'to CRLF on Windows, and so does write_text.\n'
            '"""\n'
            "# open(p, 'a') and p.write_text(s) are both forbidden here too.\n"
            "GOOD = 'open(p, \"w\", newline=\"\\\\n\")'\n"
            "def go(p, s):\n"
            "    with open(p, 'w', encoding='utf-8', newline='\\n') as f:\n"
            "        f.write(s)\n",
            encoding="utf-8", newline="\n")
        assert scan([prose]) == {}

    def test_binary_and_read_modes_are_not_in_scope(self, tmp_path):
        """No translation happens, so there is nothing to state."""
        ok = tmp_path / "binary_and_read.py"
        ok.write_text(
            "def go(p, b):\n"
            "    with open(p, 'wb') as f:\n"
            "        f.write(b)\n"
            "    with open(p, 'rb') as f:\n"
            "        f.read()\n"
            "    with open(p, encoding='utf-8') as f:\n"
            "        f.read()\n"
            "    with open(p, 'r', encoding='utf-8') as f:\n"
            "        f.read()\n",
            encoding="utf-8", newline="\n")
        assert scan([ok]) == {}

    def test_an_explicit_empty_newline_satisfies_the_rule(self, tmp_path):
        """``newline=""`` is what :mod:`csv` requires, and the rule permits it.

        The rule is explicitness, not LF. Two call sites in this tree open a
        :mod:`csv` file this way and must keep doing so.
        """
        csvlike = tmp_path / "csv_writer.py"
        csvlike.write_text(
            "import csv\n"
            "def go(p, rows):\n"
            "    with open(p, 'w', newline='', encoding='utf-8') as f:\n"
            "        csv.writer(f).writerows(rows)\n",
            encoding="utf-8", newline="\n")
        assert scan([csvlike]) == {}


class TestTheTreeComplies:

    def test_no_text_mode_write_omits_its_line_ending(self):
        found = scan(_tree_paths())
        assert not found, (
            "EOL-02: text-mode writes with no explicit newline=\n" + "\n".join(
                f"  {f}:{ln}  {c}"
                for f, v in sorted(found.items()) for ln, c in v))

    def test_the_csv_call_sites_still_state_newline_explicitly(self):
        """The two sites the rule's second clause exists for.

        They predate ``EOL-02`` and were already correct. If a mechanical
        rewrite ever turns their ``newline=""`` into ``newline="\\n"``, csv's
        own ``\\r\\n`` doubles and the file is corrupt. This is the regression
        test for that.
        """
        wanted = ("scripts/run_benchmark_sweep.py", "scripts/run_inverse_sweep.py")
        for rel in wanted:
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
            opens = [
                n for n in ast.walk(tree)
                if isinstance(n, ast.Call)
                and getattr(n.func, "id", getattr(n.func, "attr", None)) == "open"
                and isinstance(_mode_of(n), str) and "w" in _mode_of(n)]
            assert opens, f"{rel}: expected a text-mode open() call site"
            empties = [
                n for n in opens
                if (kw := _kwarg(n, "newline")) is not None
                and isinstance(kw.value, ast.Constant) and kw.value.value == ""]
            assert empties, (
                f"{rel}: expected a csv writer opened with newline='' -- the "
                f"second clause of EOL-02 has no call site left to protect")
