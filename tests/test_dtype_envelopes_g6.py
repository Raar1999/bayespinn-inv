"""PH-22 — every envelope states the dtype it was measured in.

`PH-22` was enacted after GRAD-02/GRAD-03: a stability claim measured in float64
does not transfer to a float32 training path. GRAD-02 put the ohmic-contact NaN
onset at `C_s = 1.3922e8`, the top 21.4% of the documented 1e21-1e25 m^-3 doping
range. In float32 (the dtype the networks actually train in) the onset is
`C_s = 7.079e3`, *below* the range, and 41 of 41 sampled points failed.

The generation-6 retro-sweep asked whether that was unique. It looked for
quantities used on **both** sides of the solver/network boundary, since a
single-dtype quantity cannot suffer the GRAD-02 failure mode. Two cross it:

* the SI <-> scaled doping conversion (`Scaling`), float64 in the oracle and
  float32 in the surrogate and PINN;
* `SymlogTransform`, whose output becomes a float32 training label at
  `data/splits.py:169`.

Both degrade gracefully to their dtype's epsilon rather than failing. That is a
**negative result** and is recorded as one: no second GRAD-02 was found. These
tests pin the measured envelopes so the claim cannot rot into an assumption.

`bernoulli` is deliberately included: it has exactly one definition, in NumPy, and
PH-10's "finite across the full double range" is a float64 claim. If a torch mirror
of it ever appears, the GRAD-02 failure mode becomes available again and the guard
below fails.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.surrogate.iv_surrogate import SymlogTransform

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The doping envelope the scaling comment documents, in m^-3.
DOPING_ENVELOPE = (1e16, 1e25)

#: Measured 2026-08-25 over 91 log-spaced points across DOPING_ENVELOPE.
#: Ceilings are one decade above the measurement, so a real regression trips them
#: while ordinary last-digit variation does not.
SCALING_ROUNDTRIP_CEILING = {np.float64: 1e-15, np.float32: 1e-6}

#: Measured over 122 points, I in +/-[1e-6, 1e6] A/m^2.
SYMLOG_ROUNDTRIP_CEILING = {np.float64: 1e-14, np.float32: 1e-5}


def _doping_points() -> np.ndarray:
    return np.logspace(np.log10(DOPING_ENVELOPE[0]), np.log10(DOPING_ENVELOPE[1]), 91)


class TestScalingEnvelopeIsReportedPerDtype:
    """The one quantity that crosses the solver/network boundary."""

    @pytest.mark.parametrize("dtype", [np.float64, np.float32])
    def test_roundtrip_error_stays_within_its_dtype_ceiling(self, dtype) -> None:
        worst, worst_at = 0.0, None
        for n_si in _doping_points():
            scaled = dtype(n_si) / dtype(SILICON.n_i)
            back = dtype(scaled) * dtype(SILICON.n_i)
            err = abs(float(back) - n_si) / n_si
            if err > worst:
                worst, worst_at = err, n_si
        ceiling = SCALING_ROUNDTRIP_CEILING[dtype]
        assert worst < ceiling, (
            f"PH-22 -- SI<->scaled round trip in {np.dtype(dtype).name}: max relative "
            f"error {worst:.3e} at N={worst_at:.2e} m^-3, ceiling {ceiling:.0e}"
        )

    def test_float32_is_measurably_coarser_than_float64(self) -> None:
        """The point of PH-22: the two envelopes are *different*, not interchangeable.

        Without this, both parametrisations above could pass while the code had
        silently become float64-only, and the dtype distinction PH-22 exists to
        enforce would be untested.
        """
        worsts = {}
        for dtype in (np.float64, np.float32):
            worsts[dtype] = max(
                abs(float(dtype(dtype(n) / dtype(SILICON.n_i)) * dtype(SILICON.n_i)) - n) / n
                for n in _doping_points()
            )
        assert worsts[np.float32] > worsts[np.float64] * 1e6, (
            f"float32 ({worsts[np.float32]:.3e}) is not measurably coarser than "
            f"float64 ({worsts[np.float64]:.3e}) -- is the conversion still dtype-aware?"
        )


class TestSymlogEnvelopeIsReportedPerDtype:
    """`data/splits.py:169` casts the symlog label to float32."""

    @pytest.mark.parametrize("dtype", [np.float64, np.float32])
    def test_roundtrip_error_stays_within_its_dtype_ceiling(self, dtype) -> None:
        symlog = SymlogTransform(I0=1e-6)
        currents = np.concatenate([np.logspace(-6, 6, 61), -np.logspace(-6, 6, 61)])
        worst, worst_at = 0.0, None
        for current in currents:
            forward = dtype(symlog.forward(float(current)))
            back = symlog.inverse(float(forward))
            err = abs(back - current) / abs(current)
            if err > worst:
                worst, worst_at = err, current
        ceiling = SYMLOG_ROUNDTRIP_CEILING[dtype]
        assert worst < ceiling, (
            f"PH-22 -- symlog round trip in {np.dtype(dtype).name}: max relative error "
            f"{worst:.3e} at I={worst_at:.2e} A/m^2, ceiling {ceiling:.0e}"
        )

    def test_label_noise_stays_far_below_the_published_surrogate_error(self) -> None:
        """float32 label round-trip must not approach the 2.6% median the surrogate claims."""
        symlog = SymlogTransform(I0=1e-6)
        worst = max(
            abs(symlog.inverse(float(np.float32(symlog.forward(float(i))))) - i) / abs(i)
            for i in np.concatenate([np.logspace(-6, 6, 61), -np.logspace(-6, 6, 61)])
        )
        assert worst < 2.6e-2 / 100, (
            f"float32 symlog label round-trip is {worst:.3e}, within two orders of "
            "the surrogate's published 2.6% median error -- the labels are no longer "
            "negligible against the signal"
        )


class TestBernoulliRemainsSingleDtype:
    """PH-10's 'full double range' is a float64 claim, and must stay one."""

    def test_there_is_exactly_one_definition(self) -> None:
        """SW-02: one definition per concept, so PH-10's claim covers every call site.

        AST over ``src/``, not ``git grep``. The first draft grepped the whole
        repository for ``def bernoulli`` and passed only while this file was
        untracked -- committing it made the test's own *pattern string* a match,
        and it failed on itself. That is the fourth time in this loop a
        text-matching guard has tripped on prose describing the thing it guards
        (``weights_only=False`` in g1, ``"scripts"`` in g2, ``torch`` in g6, and
        now this). The lesson is recorded rather than merely fixed: a guard whose
        subject is source code should read the syntax tree, never the characters.
        """
        import ast

        definitions = []
        for path in sorted((REPO_ROOT / "src").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            definitions += [
                f"{path.relative_to(REPO_ROOT).as_posix()}:{n.lineno}"
                for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == "bernoulli"
            ]
        assert len(definitions) == 1, (
            "PH-22 / SW-02 -- bernoulli no longer has exactly one definition, so "
            "PH-10's 'finite across the full double range' no longer covers every "
            f"call site:\n  {definitions}"
        )
        assert "scharfetter_gummel.py" in definitions[0], definitions[0]

    def test_its_body_is_numpy_only(self) -> None:
        """A torch mirror would reopen the GRAD-02 failure mode.

        Structural, not textual. The first draft of this test grepped the module
        for the string ``torch`` and failed on the *comment* added in this very
        generation to document GRAD-03 — the third time in this loop that a
        substring guard tripped on prose describing the finding it guards. An AST
        walk over the function body cannot be satisfied or broken by a comment.
        """
        import ast

        module = ast.parse(
            (REPO_ROOT / "src" / "bayespinn_inv" / "solvers" / "scharfetter_gummel.py")
            .read_text(encoding="utf-8")
        )
        func = next(
            (n for n in ast.walk(module)
             if isinstance(n, ast.FunctionDef) and n.name == "bernoulli"),
            None,
        )
        assert func is not None, "bernoulli is no longer defined where PH-10 says it is"

        torch_uses = [
            n.lineno for n in ast.walk(func)
            if (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                and n.value.id == "torch")
            or (isinstance(n, ast.Name) and n.id == "torch")
        ]
        assert not torch_uses, (
            f"PH-22 -- bernoulli's body reaches torch at lines {torch_uses}. PH-10's "
            "'finite across the full double range' is a float64 claim; a float32 "
            "path needs its own measured envelope."
        )

    def test_the_module_does_not_import_torch(self) -> None:
        import ast

        module = ast.parse(
            (REPO_ROOT / "src" / "bayespinn_inv" / "solvers" / "scharfetter_gummel.py")
            .read_text(encoding="utf-8")
        )
        imports = [
            n.lineno for n in ast.walk(module)
            if (isinstance(n, ast.Import) and any(a.name.split(".")[0] == "torch" for a in n.names))
            or (isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "torch")
        ]
        assert not imports, (
            f"PH-22 -- the SG oracle imports torch at lines {imports}. It is the "
            "float64 arbiter; a torch dependency means some path through it may now "
            "be float32 and every envelope it publishes needs re-measuring."
        )
