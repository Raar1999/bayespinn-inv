"""The lint verdict is one verdict: `ruff check .` and the scoped invocation agree.

The defect that forced this
---------------------------
The generation-8 state file recorded

    "ruff_exit": 0

and nothing else. `mypy_findings: 25` beside it carried its scope and the method
that produced it; `ruff_exit` carried neither. That would be a documentation nit
if the two defensible scopes agreed. They did not:

* `ruff check .`                     exit **1**, 107 findings
* `ruff check src tests scripts`     exit **0**

One verdict was recorded and two existed, and every finding in the gap lived in
`notebooks/`, which are generated artefacts written by
`scripts/build_notebooks.py` and shipped with executed outputs.

The ruling of 2026-08-26 section 3 rejected annotating the ambiguity and required
eliminating it: configure ruff so both invocations return the same verdict over
the tracked tree. `pyproject.toml`'s `[tool.ruff.lint.per-file-ignores]` block
does that, and this module is its guard.

Why an ignore block needs a guard at all
----------------------------------------
An ignore list that grows quietly is a way of making a lint run mean nothing.
Three properties are asserted, not assumed:

1. the two scopes agree, and agree at **0** -- the property the ruling asked for;
2. the block is **not a blanket amnesty** -- a defect ruff would still catch in a
   notebook still fails (positive control);
3. the three findings that are real untidiness rather than layout are pinned
   **exactly**, in both directions, so that fixing the generator is a visible
   action and a *new* one cannot arrive unnoticed.

`SW-20`: the subject here is a lint configuration and a set of generated JSON
documents, so there is no AST of ours to walk -- ruff does that walking. The two
controls the rule requires are implemented as (2) above and
:meth:`TestTheBlockIsNotABlanketAmnesty.test_the_generator_layout_idioms_are_not_flagged`,
and this docstring is the prose that names every suppressed code without being a
suppression of them.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
NB_DIR = ROOT / "notebooks"

#: The two scopes that were in tension. Both must now return the same verdict.
SCOPES = (
    ("whole tree", ["."]),
    ("src tests scripts", ["src", "tests", "scripts"]),
)

#: The three findings in `notebooks/` that are NOT layout artefacts of the
#: generator: they are untidiness in the source strings inside
#: `scripts/build_notebooks.py`. They are suppressed rather than fixed because
#: fixing them means regenerating, and regenerating discards the executed
#: outputs that make the notebooks evidence (NB-01). Enumerating them here is
#: what keeps "suppressed" from sliding into "forgotten": this list is asserted
#: **exactly**, so repairing the generator fails this test by design and the
#: failure is the signal to shorten the list.
KNOWN_GENERATOR_UNTIDINESS = {
    ("01_setup.ipynb", "F401"),
    ("04_forward_surrogate.ipynb", "F541"),
    ("05_inverse_design.ipynb", "B007"),
}

#: Codes the block suppresses that are consequences of the generator's *layout*
#: -- how cells are emitted, not what they do.
LAYOUT_CODES = {"I001", "E401", "E402", "E701"}

#: Entailed by disabling F401 in files carrying a deliberate F401 suppression
#: comment: the suppression becomes unused, which is what RUF100 reports.
#: It does not appear while F401 is enabled, so it is excluded from the
#: "every listed code is load-bearing" assertion below and named here instead.
ENTAILED_CODES = {"RUF100"}


def _ruff(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", *args],
        capture_output=True, text=True, cwd=str(cwd))


def _ruff_available() -> bool:
    try:
        import ruff as _ruff_pkg
    except ImportError:
        return shutil.which("ruff") is not None
    return _ruff_pkg is not None


pytestmark = pytest.mark.skipif(
    not _ruff_available(), reason="ruff is not installed in this environment")


def _notebook(*cells: str) -> str:
    """A minimal nbformat-4 document ruff will lint, one code cell per source."""
    return json.dumps({
        "cells": [{"cell_type": "code", "execution_count": None,
                   "metadata": {}, "outputs": [], "source": c.splitlines(True)}
                  for c in cells],
        "metadata": {"kernelspec": {"display_name": "Python 3",
                                    "language": "python", "name": "python3"},
                     "language_info": {"name": "python", "version": "3.11.9"}},
        "nbformat": 4, "nbformat_minor": 5,
    }, indent=1)


def _tree_with_config(tmp_path: Path, notebook_source: str) -> Path:
    """A throwaway tree carrying THIS repository's ruff configuration.

    The per-file-ignore pattern is relative to the directory holding the
    configuration, so the control notebooks have to live under a `notebooks/`
    directory beside a copy of the real `pyproject.toml`. Copying the file
    rather than restating the rules is deliberate: a control that restated them
    would pass while the real configuration said something else.
    """
    shutil.copyfile(PYPROJECT, tmp_path / "pyproject.toml")
    nb_dir = tmp_path / "notebooks"
    nb_dir.mkdir()
    (nb_dir / "control.ipynb").write_text(notebook_source, encoding="utf-8", newline="\n")
    return nb_dir / "control.ipynb"


def _codes(proc: subprocess.CompletedProcess) -> set:
    """Rule codes in a `--output-format=concise` run."""
    out = set()
    for line in proc.stdout.splitlines():
        parts = line.split(": ", 1)
        if len(parts) == 2 and parts[0].count(":") >= 2:
            out.add(parts[1].split(" ", 1)[0].lstrip("[").rstrip("]"))
    return out


class TestTheTwoScopesAgree:
    """The property the ruling asked for, stated as an assertion."""

    def test_both_invocations_return_the_same_exit_code(self):
        results = {name: _ruff(*paths) for name, paths in SCOPES}
        codes = {name: p.returncode for name, p in results.items()}
        assert len(set(codes.values())) == 1, (
            "the two defensible lint scopes disagree, which is the defect this "
            f"configuration exists to remove: {codes}\n\n"
            + "\n".join(f"--- {n} ---\n{p.stdout[-2000:]}"
                        for n, p in results.items()))

    def test_both_invocations_are_clean(self):
        for name, paths in SCOPES:
            proc = _ruff(*paths)
            assert proc.returncode == 0, (
                f"`ruff check {' '.join(paths)}` ({name}) exited "
                f"{proc.returncode}:\n{proc.stdout[-2000:]}")

    def test_neither_scope_is_clean_only_because_it_looks_at_nothing(self):
        """A scope that lints no files exits 0 too.

        `ruff check .` returning 0 is evidence only if it actually reached the
        notebooks -- the files whose findings were the whole discrepancy. This
        counts what each invocation checked.
        """
        for name, paths in SCOPES:
            proc = _ruff("--statistics", *paths)
            assert proc.returncode == 0, name
        proc = _ruff("--config", "lint.per-file-ignores = {}",
                     "--output-format=concise", ".")
        touched = {line.split(":", 1)[0].replace("\\", "/").split("/")[0]
                   for line in proc.stdout.splitlines() if ":" in line}
        assert "notebooks" in touched, (
            "`ruff check .` is not reaching notebooks/ at all, so its exit 0 "
            "says nothing about them; the scopes would agree by exclusion "
            "rather than by configuration")


class TestTheBlockIsNotABlanketAmnesty:
    """`SW-20`'s two controls: it must fire, and it must not over-fire."""

    def test_a_real_defect_in_a_notebook_is_still_caught(self, tmp_path):
        """Positive control. `F821` is not suppressed and must still fail."""
        target = _tree_with_config(
            tmp_path,
            _notebook("import numpy as np\nnp.array(undefined_name_xyz)\n"))
        proc = _ruff("--output-format=concise", str(target), cwd=tmp_path)
        assert proc.returncode == 1 and "F821" in _codes(proc), (
            "the notebook ignore block has become a blanket amnesty: a "
            "plainly undefined name in a notebook cell was not reported.\n"
            f"exit={proc.returncode}\n{proc.stdout}")

    def test_the_generator_layout_idioms_are_not_flagged(self, tmp_path):
        """Negative control: exactly what `build_notebooks.py` emits, quiet."""
        target = _tree_with_config(tmp_path, _notebook(
            "import sys, os\n"
            "IN_COLAB = 'google.colab' in sys.modules\n"
            "import numpy as np, matplotlib.pyplot as plt\n",
            "from pathlib import Path\n"
            "zs = []\n"
            "for s in [1.0, 2.0]:\n"
            "    if s > 1e-9: zs.append(s)\n"
            "print(Path('.').name, os.getcwd(), np.array(zs), plt)\n",
        ))
        proc = _ruff("--output-format=concise", str(target), cwd=tmp_path)
        assert proc.returncode == 0, (
            "the generator's own cell layout is being reported, so the "
            "configuration does not describe the artefacts it covers:\n"
            + proc.stdout)


class TestTheSuppressedSetIsPinned:
    """What the block hides is enumerated, and the enumeration is exact."""

    @staticmethod
    def _unsuppressed():
        """Every notebook finding, with per-file-ignores cleared."""
        proc = _ruff("--config", "lint.per-file-ignores = {}",
                     "--output-format=concise", "notebooks")
        found = set()
        for line in proc.stdout.splitlines():
            if not line.startswith("notebooks"):
                continue
            head, _, rest = line.partition(": ")
            code = rest.split(" ", 1)[0]
            name = head.split(":", 1)[0].replace("\\", "/").split("/")[-1]
            found.add((name, code))
        return found

    def test_the_known_untidiness_is_exactly_what_is_listed(self):
        found = self._unsuppressed()
        real = {(n, c) for (n, c) in found if c not in LAYOUT_CODES}
        assert real == KNOWN_GENERATOR_UNTIDINESS, (
            "the non-layout findings in notebooks/ are not the ones this guard "
            "records.\n"
            f"  newly present : {sorted(real - KNOWN_GENERATOR_UNTIDINESS)}\n"
            f"  now absent    : {sorted(KNOWN_GENERATOR_UNTIDINESS - real)}\n"
            "If the generator was repaired, shorten KNOWN_GENERATOR_UNTIDINESS "
            "and the matching comment in pyproject.toml. If something new "
            "arrived, it is a finding, not a formatting difference.")

    def test_every_suppressed_code_actually_occurs(self):
        """No speculative entries: a listed code must be doing work.

        An ignore list padded with codes nothing produces is how a narrow
        exemption turns into a wide one without anybody deciding to widen it.
        """
        listed = self._listed_codes()
        found = {c for (_, c) in self._unsuppressed()}
        idle = listed - found - ENTAILED_CODES
        assert not idle, (
            f"these codes are suppressed for notebooks/ but nothing in "
            f"notebooks/ produces them: {sorted(idle)}")

    def test_nothing_is_suppressed_that_is_not_listed(self):
        listed = self._listed_codes()
        found = {c for (_, c) in self._unsuppressed()}
        assert found <= listed, (
            f"findings suppressed by scope rather than by decision: "
            f"{sorted(found - listed)}")

    @staticmethod
    def _listed_codes() -> set:
        """The codes `pyproject.toml` actually grants to `notebooks/*.ipynb`."""
        text = PYPROJECT.read_text(encoding="utf-8")
        marker = '"notebooks/*.ipynb" = ['
        i = text.index(marker) + len(marker)
        body = text[i:text.index("]", i)]
        return {tok.strip().strip('"')
                for line in body.splitlines()
                for tok in line.split("#", 1)[0].split(",")
                if tok.strip().strip('"')}
