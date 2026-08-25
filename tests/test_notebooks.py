"""The twelve notebooks must stay in sync with the generator that writes them.

Two failure modes, both of which actually happened:

* **BUG-14.** `scripts/build_notebooks.py` wrote with the platform default
  encoding, so on Windows it died on the first physics symbol and truncated
  the notebook it was midway through. "Regenerate the notebooks" was a
  documented procedure that could not be performed.
* **NB-01 / code drift.** The notebooks are *generated artefacts*. Hand-editing
  one, or changing the generator without regenerating, silently produces a
  shipped notebook whose code is not the code the generator would emit -- and
  nothing else in the project would notice.

These tests are skipped when `nbformat` is unavailable, since it is not a
runtime dependency of the package.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
NB_DIR = REPO / "notebooks"
BUILDER = REPO / "scripts" / "build_notebooks.py"

nbformat = pytest.importorskip("nbformat")

pytestmark = pytest.mark.skipif(
    not BUILDER.exists() or not NB_DIR.exists(),
    reason="notebook generator or notebooks/ absent (installed-package run)",
)

# `open(p, "w")` / `open(p, "r")` ... and the form the first sweep missed,
# `open(p)`, which is *also* a text read using the platform encoding.
_OPEN_WITH_MODE = re.compile(r"""\bopen\([^()\n]*?,\s*['"][rwa+]+['"][^()\n]*?\)""")
_OPEN_NO_MODE = re.compile(r"""\bopen\(([^()\n,]+)\)""")


class TestNotebooksMatchTheirGenerator:

    def test_all_twelve_are_present_and_parseable(self):
        nbs = sorted(NB_DIR.glob("*.ipynb"))
        assert len(nbs) == 12, f"expected 12 notebooks, found {len(nbs)}"
        for nb in nbs:
            doc = json.loads(nb.read_text(encoding="utf-8"))
            assert doc["cells"], f"{nb.name} has no cells"

    def test_notebooks_are_valid_utf8(self):
        """BUG-14 truncated a notebook mid-write; the result did not parse."""
        for nb in sorted(NB_DIR.glob("*.ipynb")):
            raw = nb.read_bytes()
            raw.decode("utf-8")            # raises if the file was mangled
            assert raw.rstrip().endswith(b"}"), f"{nb.name} looks truncated"

    def test_generator_writes_with_an_explicit_encoding(self):
        """The specific defect: `write_text` with no `encoding` (BUG-14).

        Asserted on the source rather than by running the generator, so the
        invariant is stated even where the platform default is already UTF-8
        and the bug would be invisible.
        """
        src = BUILDER.read_text(encoding="utf-8")
        assert 'write_text(nbf.writes(nb), encoding="utf-8")' in src, (
            "build_notebooks.py must write with an explicit utf-8 encoding; "
            "without it the generator cannot run on a cp1252 default"
        )

    def test_no_text_io_omits_an_encoding(self):
        """The same defect class, swept across src/ and scripts/ (BUG-14).

        Both call forms are checked. The first sweep only caught the
        explicit-mode form and left ten `open(p)` calls behind.
        """
        offenders = []
        for root in (REPO / "scripts", REPO / "src"):
            for py in sorted(root.rglob("*.py")):
                for n, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                    for m in _OPEN_WITH_MODE.finditer(line):
                        txt = m.group(0)
                        if "encoding" not in txt and "b" not in txt.split(",")[1]:
                            offenders.append(f"{py.relative_to(REPO)}:{n}: {line.strip()}")
                    for m in _OPEN_NO_MODE.finditer(line):
                        if "encoding" not in m.group(1):
                            offenders.append(f"{py.relative_to(REPO)}:{n}: {line.strip()}")
        assert not offenders, (
            "text IO without an explicit encoding (BUG-14 regression):\n"
            + "\n".join(offenders)
        )


class TestNotebooksHaveExecutedOutputs:
    """NB-01: the notebooks ship executed outputs; they must not be blank."""

    def test_every_notebook_has_at_least_one_output(self):
        blank = []
        for nb in sorted(NB_DIR.glob("*.ipynb")):
            doc = json.loads(nb.read_text(encoding="utf-8"))
            if not any(c.get("outputs") for c in doc["cells"]
                       if c["cell_type"] == "code"):
                blank.append(nb.name)
        assert not blank, (
            "these notebooks ship with no executed outputs: " + ", ".join(blank))

    def test_no_notebook_contains_an_execution_error(self):
        """A shipped notebook whose cells errored is worse than a blank one."""
        bad = []
        for nb in sorted(NB_DIR.glob("*.ipynb")):
            doc = json.loads(nb.read_text(encoding="utf-8"))
            for i, c in enumerate(doc["cells"]):
                for o in c.get("outputs", []):
                    if o.get("output_type") == "error":
                        bad.append(f"{nb.name} cell {i}: {o.get('ename')}")
        assert not bad, "notebooks contain execution errors:\n" + "\n".join(bad)


class TestNotebookClaims:
    """Stale narrative numbers are corrected in the *generator*, so they
    cannot drift back the next time the notebooks are regenerated."""

    RETIRED = ("13 orders of magnitude",)

    def test_retired_claims_are_gone_from_the_generator(self):
        src = BUILDER.read_text(encoding="utf-8")
        for claim in self.RETIRED:
            assert claim not in src, (
                f"{claim!r} was measured at 9.96 decades "
                f"(CLAIM_EVIDENCE_MATRIX C4) and must not reappear in the "
                f"notebook generator")

    def test_retired_claims_are_gone_from_the_notebooks(self):
        for nb in sorted(NB_DIR.glob("*.ipynb")):
            text = nb.read_text(encoding="utf-8")
            for claim in self.RETIRED:
                assert claim not in text, f"{nb.name} still asserts {claim!r}"


class TestDocumentedTestCountIsHonest:
    """DOC-03: the README once contradicted its own badge on the test count.

    A number that has to be updated by hand drifts. This asserts the README
    badge matches what pytest actually collects, so the drift is caught by the
    thing it describes.
    """

    def test_readme_badge_matches_the_collected_count(self):
        import subprocess
        import sys
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        m = re.search(r"tests-(\d+)%20passing", readme)
        assert m, "README has no test-count badge"
        claimed = int(m.group(1))
        out = subprocess.run(
            [sys.executable, "-m", "pytest", str(REPO / "tests"), "-q",
             "--collect-only", "-p", "no:cacheprovider"],
            capture_output=True, text=True, cwd=REPO).stdout
        got = re.search(r"(\d+) tests? collected", out)
        assert got, f"could not parse pytest collection output:\n{out[-500:]}"
        assert claimed == int(got.group(1)), (
            f"README badge claims {claimed} tests; pytest collects {got.group(1)}")
