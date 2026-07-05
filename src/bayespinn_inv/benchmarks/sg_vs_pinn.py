"""
Benchmark harness: ScharfetterGummel vs PINN.

We compare on:
- **Pointwise field accuracy**: max/RMS error in phi, n, p across the
  device, at a sweep of biases.
- **I-V accuracy**: relative error in terminal current at each bias,
  with special attention to the high-bias regime where the SG solution
  is most "informative".
- **Wall-clock and memory**: time per forward solve (SG batched
  vs single PINN inference, vs ensemble M*PINN inference).

The harness is solver-agnostic — it expects both solvers to expose the
:meth:`solve(doping_si, bias) -> DeviceState` contract.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch


@dataclass
class BenchmarkResult:
    biases: np.ndarray
    phi_rms_error: np.ndarray         # (B,)
    phi_max_error: np.ndarray         # (B,)
    n_log_rms_error: np.ndarray       # log10 RMS
    p_log_rms_error: np.ndarray
    I_relative_error: np.ndarray
    time_per_solve_sg: float
    time_per_solve_pinn: float
    n_points_compared: int


def compare_solvers(
    sg_solver,
    pinn_solver,
    doping_si: torch.Tensor,
    biases: Sequence[float],
    warmup: int = 1,
) -> BenchmarkResult:
    """Compare SG and PINN on the same doping profile across biases."""
    biases_arr = np.asarray(biases, dtype=float)
    B = len(biases_arr)

    # 1) SG ground-truth solves
    sg_states = []
    # warm-up to amortize lazy imports / JIT
    for _ in range(warmup):
        sg_solver.solve(doping_si.detach().cpu().numpy()
                          if isinstance(doping_si, torch.Tensor)
                          else doping_si, float(biases_arr[0]))
    t0 = time.perf_counter()
    for V in biases_arr:
        dop_np = (doping_si.detach().cpu().numpy()
                    if isinstance(doping_si, torch.Tensor) else doping_si)
        sg_states.append(sg_solver.solve(dop_np, float(V)))
    t_sg = (time.perf_counter() - t0) / B

    # 2) PINN solves
    for _ in range(warmup):
        pinn_solver.solve(doping_si, float(biases_arr[0]))
    t0 = time.perf_counter()
    pinn_states = []
    for V in biases_arr:
        pinn_states.append(pinn_solver.solve(doping_si, float(V)))
    t_pinn = (time.perf_counter() - t0) / B

    # 3) Error metrics. We compare on the SG grid (interpolate the PINN
    #    output to the SG grid for fairness).
    phi_rms = np.empty(B); phi_max = np.empty(B)
    n_rms = np.empty(B); p_rms = np.empty(B)
    I_rel = np.empty(B)
    for i, (s_sg, s_pinn) in enumerate(zip(sg_states, pinn_states)):
        x_ref = s_sg.x
        phi_pinn = np.interp(x_ref, s_pinn.x, s_pinn.phi)
        n_pinn   = np.interp(x_ref, s_pinn.x, s_pinn.n)
        p_pinn   = np.interp(x_ref, s_pinn.x, s_pinn.p)
        phi_rms[i] = float(np.sqrt(np.mean((phi_pinn - s_sg.phi) ** 2)))
        phi_max[i] = float(np.max(np.abs(phi_pinn - s_sg.phi)))
        # log-space carrier RMS (only where SG has reasonable signal)
        eps = 1e6   # m^-3 floor
        log_n_sg   = np.log10(np.maximum(s_sg.n, eps))
        log_n_pinn = np.log10(np.maximum(n_pinn, eps))
        log_p_sg   = np.log10(np.maximum(s_sg.p, eps))
        log_p_pinn = np.log10(np.maximum(p_pinn, eps))
        n_rms[i] = float(np.sqrt(np.mean((log_n_pinn - log_n_sg) ** 2)))
        p_rms[i] = float(np.sqrt(np.mean((log_p_pinn - log_p_sg) ** 2)))
        # terminal current via mean of total current
        I_sg = float(np.mean(s_sg.Jn + s_sg.Jp))
        I_pinn = float(np.mean(s_pinn.Jn + s_pinn.Jp))
        denom = max(abs(I_sg), 1e-9)
        I_rel[i] = float(abs(I_pinn - I_sg) / denom)

    return BenchmarkResult(
        biases=biases_arr,
        phi_rms_error=phi_rms, phi_max_error=phi_max,
        n_log_rms_error=n_rms, p_log_rms_error=p_rms,
        I_relative_error=I_rel,
        time_per_solve_sg=t_sg, time_per_solve_pinn=t_pinn,
        n_points_compared=len(sg_states[0].x),
    )


def format_benchmark_table(res: BenchmarkResult) -> str:
    """Pretty-print benchmark results as a Markdown table."""
    rows = []
    rows.append("| Bias (V) | phi RMS (V) | phi max (V) | log10(n) RMS | log10(p) RMS | |dI|/I |")
    rows.append("|---:|---:|---:|---:|---:|---:|")
    for i, V in enumerate(res.biases):
        rows.append(
            f"| {V:.3f} | "
            f"{res.phi_rms_error[i]:.3e} | "
            f"{res.phi_max_error[i]:.3e} | "
            f"{res.n_log_rms_error[i]:.3f} | "
            f"{res.p_log_rms_error[i]:.3f} | "
            f"{res.I_relative_error[i]:.3e} |"
        )
    rows.append("")
    rows.append(f"Time/solve: SG {res.time_per_solve_sg*1e3:.1f} ms, "
                f"PINN {res.time_per_solve_pinn*1e3:.1f} ms "
                f"({res.time_per_solve_sg/max(res.time_per_solve_pinn,1e-9):.1f}x)")
    return "\n".join(rows)


__all__ = ["BenchmarkResult", "compare_solvers", "format_benchmark_table"]
