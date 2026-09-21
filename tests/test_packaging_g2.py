"""Regression tests for AUDIT_g0 PKG-04 — library code execs a file from the checkout.

`SW-17`: never ``exec`` or ``import`` a file from a source checkout path at
runtime. ``surrogate/adapters.py`` still does:

    spec = importlib.util.spec_from_file_location("_rbs", legacy)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_rbs"] = mod
    spec.loader.exec_module(mod)
    return mod.load_ensemble(Path(manifest_path))

where ``legacy`` is ``Path(__file__).resolve().parents[3] / "scripts" /
"run_benchmark_sweep.py"`` -- the repository's ``scripts/`` directory, which is
not part of the wheel.

The first audit cycle recorded this as ``PKG-02`` and closed it. The close
improved only the *error message* raised when ``scripts/`` is absent; the
``exec_module`` call itself survived. This is the defect-class recurrence check
in `AUDIT_g0` §4 doing its job: the fixed instance was not the fixed pattern.

Reachability -- measured, not assumed
-------------------------------------
The branch is live. ``outputs/smoke/manifest.json`` carries ``checkpoints`` and no
``type`` key, so ``load_forward_ensemble`` takes the legacy path for it. Deleting
the branch would therefore remove a capability a shipped artefact still
exercises, which is why the fix is a *move into the package* rather than a
deletion -- or an explicit retirement under `M-22` with an ADR.

These tests are written before either fix exists (`AH-08`).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LIBRARY = REPO_ROOT / "src" / "bayespinn_inv"

#: Names that load and execute a module from an arbitrary filesystem path.
FORBIDDEN = {"spec_from_file_location", "exec_module", "module_from_spec"}


def _forbidden_calls(path: Path):
    """(line, name) for every dynamic-module-loading call in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name in FORBIDDEN:
            out.append((node.lineno, name))
    return out


LIBRARY_FILES = sorted(LIBRARY.rglob("*.py"))


class TestLibraryNeverExecutesAFileFromTheCheckout:
    """SW-17, and the pattern behind PKG-02 rather than its fixed instance."""

    @pytest.mark.parametrize(
        "path", LIBRARY_FILES, ids=[p.relative_to(LIBRARY).as_posix() for p in LIBRARY_FILES]
    )
    def test_no_dynamic_module_loading(self, path: Path) -> None:
        offenders = [
            f"{path.relative_to(REPO_ROOT).as_posix()}:{line} -> {name}()"
            for line, name in _forbidden_calls(path)
        ]
        assert not offenders, (
            "AUDIT_g0 PKG-04 / SW-17 -- library code loads and executes a module "
            "from a filesystem path:\n  " + "\n  ".join(offenders)
        )

    def test_the_scanner_is_not_vacuous(self) -> None:
        """Negative control: the check must fire on the pattern it claims to find."""
        sample = (
            "import importlib.util\n"
            "def f(p):\n"
            "    spec = importlib.util.spec_from_file_location('m', p)\n"
            "    mod = importlib.util.module_from_spec(spec)\n"
            "    spec.loader.exec_module(mod)\n"
            "    return mod\n"
        )
        tree = ast.parse(sample)
        found = {
            (node.func.attr if isinstance(node.func, ast.Attribute)
             else getattr(node.func, "id", None))
            for node in ast.walk(tree) if isinstance(node, ast.Call)
        }
        assert FORBIDDEN & found == FORBIDDEN, (
            f"the scanner would miss the pattern it exists to catch: found {found}"
        )

    def test_no_library_module_reaches_for_the_scripts_directory(self) -> None:
        """The specific shape of PKG-02/PKG-04: ``parents[3] / "scripts"``.

        AST-level, deliberately. A substring search for ``"scripts"`` matches the
        comments that *document* the finding, and could be satisfied by deleting
        a comment rather than by removing code -- the same trap this suite fell
        into once already in generation 1 with ``weights_only=False``. Comments do
        not appear in an AST, so a string-literal walk can only be satisfied by
        removing the literal from actual code.
        """
        offenders = []
        for path in LIBRARY_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and node.value == "scripts":
                    offenders.append(
                        f"{path.relative_to(REPO_ROOT).as_posix()}:{node.lineno}"
                    )
        assert not offenders, (
            "AUDIT_g0 PKG-04 -- library code names the repository's scripts/ "
            f"directory in code, and it is not packaged: {offenders}"
        )


class TestTheLegacyBranchIsReachable:
    """Documents *why* the fix must be a move, not a deletion."""

    SMOKE = REPO_ROOT / "outputs" / "smoke" / "manifest.json"

    @pytest.mark.skipif(not SMOKE.is_file(), reason="outputs/smoke/manifest.json absent")
    def test_a_shipped_manifest_still_takes_the_legacy_path(self) -> None:
        manifest = json.loads(self.SMOKE.read_text(encoding="utf-8"))
        assert manifest.get("type") != "surrogate", (
            "outputs/smoke/manifest.json now declares type='surrogate'; the legacy "
            "branch may be unreachable and this test should be revisited"
        )
        assert "checkpoints" in manifest, (
            "outputs/smoke/manifest.json no longer carries checkpoints, so it is "
            "not an ensemble manifest and does not exercise the legacy branch"
        )
