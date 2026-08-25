"""Regression tests for AUDIT_g0 SEC-02 — unsafe checkpoint loading.

`SW-16`: ``torch.load`` is always ``weights_only=True``. Loading a checkpoint is
never allowed to execute code. Two places in library code broke that:

``training/trainer.py:386``
    ``torch.load(path, map_location=..., weights_only=False)`` unconditionally.
    No warning, no fallback, no condition -- every checkpoint load ran arbitrary
    pickle.

``surrogate/adapters.py:237``
    Tried ``weights_only=True`` first, then fell back to ``weights_only=False``
    behind a ``warnings.warn``. `SW-03` is explicit that a degraded path must
    return a status flag the caller is forced to read, or raise -- a warning is
    neither. Warnings are routinely filtered, and by the time one is emitted the
    unsafe load is already about to happen.

Measured before the fix: **all seven** checkpoints shipped in ``outputs/`` load
cleanly under ``weights_only=True``:

    outputs/pinn_vs_surrogate/pinn/ckpt_final.pt      dict(model_state, opt_state, cfg, weights)
    outputs/smoke/member_000/ckpt_final.pt            dict(model_state, opt_state, cfg, weights)
    outputs/surrogate_ensemble/surrogate_member_00{0..4}.pt   dict(state_dict, cfg)

So the fallback was never load-bearing: it was dead code guarding a capability
nothing in the repository needs. Removing it costs nothing and closes the hole.
"""

from __future__ import annotations

import ast
import glob
from pathlib import Path
from typing import List, Tuple

import pytest
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
LIBRARY = REPO_ROOT / "src" / "bayespinn_inv"


def _torch_load_calls(path: Path) -> List[Tuple[int, ast.Call]]:
    """Every ``torch.load(...)`` call in ``path``, with its line number."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (func.attr if isinstance(func, ast.Attribute)
                else func.id if isinstance(func, ast.Name) else None)
        if name == "load" and isinstance(func, ast.Attribute):
            base = func.value
            if isinstance(base, ast.Name) and base.id == "torch":
                out.append((node.lineno, node))
    return out


def _weights_only_value(call: ast.Call):
    """The literal passed as ``weights_only``, or ``None`` if absent."""
    for kw in call.keywords:
        if kw.arg == "weights_only":
            return ast.literal_eval(kw.value) if isinstance(kw.value, ast.Constant) else "<dynamic>"
    return None


LIBRARY_FILES = sorted(LIBRARY.rglob("*.py"))


class TestLibraryNeverLoadsCheckpointsUnsafely:
    """SW-16: no library code path may execute code from a checkpoint."""

    @pytest.mark.parametrize(
        "path", LIBRARY_FILES, ids=[p.relative_to(LIBRARY).as_posix() for p in LIBRARY_FILES]
    )
    def test_every_torch_load_is_weights_only(self, path: Path) -> None:
        offenders = [
            f"{path.relative_to(REPO_ROOT).as_posix()}:{lineno} -> weights_only={value!r}"
            for lineno, call in _torch_load_calls(path)
            for value in [_weights_only_value(call)]
            if value is not True
        ]
        assert not offenders, (
            "AUDIT_g0 SEC-02 / SW-16 -- torch.load in library code without "
            "weights_only=True:\n  " + "\n  ".join(offenders)
        )

    def test_the_scan_actually_finds_torch_load_calls(self) -> None:
        """Negative control: a scanner that matches nothing would pass vacuously."""
        total = sum(len(_torch_load_calls(p)) for p in LIBRARY_FILES)
        assert total > 0, (
            "the AST scan found no torch.load calls anywhere in the library -- "
            "it is not testing what it claims to test"
        )

    def test_no_torch_load_hides_inside_an_exception_handler(self) -> None:
        """SW-03: no ``except:`` may retry the load on a laxer setting.

        The check is structural rather than textual. A substring search for
        ``weights_only=False`` would be satisfied by deleting a *comment* that
        documents the finding, and would flag this very file; an AST walk over
        ``ExceptHandler`` bodies can only be satisfied by removing the code.
        """
        offenders = []
        for path in LIBRARY_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Call) and inner in [
                        c for _, c in _torch_load_calls(path)
                    ]:
                        offenders.append(
                            f"{path.relative_to(REPO_ROOT).as_posix()}:{inner.lineno}"
                        )
        assert not offenders, (
            "AUDIT_g0 SEC-02 / SW-03 -- torch.load inside an exception handler, "
            f"i.e. a fallback the caller is never forced to read: {offenders}"
        )


class TestTheShippedCheckpointsDoNotNeedTheFallback:
    """The measurement that makes removing the fallback safe rather than hopeful."""

    CHECKPOINTS = sorted(glob.glob(str(REPO_ROOT / "outputs" / "**" / "*.pt"), recursive=True))

    @pytest.mark.skipif(not CHECKPOINTS, reason="no checkpoints in outputs/")
    def test_every_shipped_checkpoint_loads_safely(self) -> None:
        failures = []
        for path in self.CHECKPOINTS:
            try:
                torch.load(path, map_location="cpu", weights_only=True)
            except Exception as exc:
                failures.append(f"{Path(path).name}: {type(exc).__name__}: {exc}")
        assert not failures, (
            "a checkpoint in outputs/ needs unsafe loading, so removing the "
            "fallback would remove a load-bearing capability:\n  " + "\n  ".join(failures)
        )
