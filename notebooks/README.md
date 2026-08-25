# Notebooks

> ## ✅ Re-executed against the current code
>
> All twelve notebooks were regenerated from `scripts/build_notebooks.py` and
> **re-executed top to bottom** after the audit in `docs/AUDIT_MASTER.md`,
> against the current Scharfetter-Gummel solver (including the BUG-13 fix).
> Their embedded outputs and figures are current, and the narrative numbers
> that were wrong before have been corrected in the generator:
>
> * "13 orders of magnitude" -> the measured training-label range is **9.96
>   decades**;
> * "~4% I-V error" -> **2.8% interpolation, 38% extrapolation, 84% family
>   transfer** on disjoint splits;
> * "~500x speed" -> **152x** for the M=5 ensemble;
> * notebook `08` is a bias-informativeness study, **not** a demonstration
>   that active learning helps. Measured properly against inverse
>   identifiability, uncertainty-driven acquisition is **worse than random**
>   (AUDIT_MASTER DES-01: −0.31 rank, 9 losses of 20); information-based
>   design is the strategy that works (+0.39, 0 losses).
>
> The notebooks are regenerated, not hand-edited: fix
> `scripts/build_notebooks.py`, re-run it, then re-execute. Canonical numbers
> live in `outputs/results/results_summary.md` and
> `docs/CLAIM_EVIDENCE_MATRIX.md`; the notebooks are the illustrated tour.

Twelve Colab-ready notebooks, each self-contained and runnable independently
(they clone + install the package on Colab, or add `./src` to the path locally).
All ship with **executed outputs and figures** — open any one to see real
results without running anything. Every number is measured against the
Scharfetter–Gummel drift-diffusion solver.

**New here? Open `12_demo.ipynb` first** — the full forward → inverse →
uncertainty story in under a minute.

| # | Notebook | What it shows |
|---|---|---|
| 01 | `01_setup.ipynb` | Environment, Drive mount, install, sanity check |
| 02 | `02_physics_validation.ipynb` | Built-in potential (matches analytic to 0.00%), band picture |
| 03 | `03_sg_solver.ipynb` | The SG oracle: I–V dynamic range, ideality factor (1.018) |
| 04 | `04_forward_surrogate.ipynb` | **The forward model** — SG-supervised surrogate, 2.8% interpolation error |
| 05 | `05_inverse_design.ipynb` | Recover doping from I–V by gradient descent through the surrogate |
| 06 | `06_mc_dropout.ipynb` | Uncertainty via MC-Dropout |
| 07 | `07_deep_ensemble.ipynb` | Uncertainty via deep ensemble |
| 08 | `08_active_learning.ipynb` | Which biases to measure — bias informativeness (no measured AL advantage) |
| 09 | `09_calibration.ipynb` | Coverage diagnosis (overconfident) + temperature-scaling fix |
| 10 | `10_benchmarking.ipynb` | Accuracy + speed vs SG (**152×** for the M=5 ensemble) |
| 11 | `11_visualization.ipynb` | Publication-figure gallery |
| 12 | `12_demo.ipynb` | **End-to-end demo** — forward → inverse → calibrated uncertainty |

## Why the forward model is a surrogate, not a pure-physics PINN

A pure-physics PINN cannot reproduce diode I–V here: the terminal current is a
numerically-fragile derived quantity dominated by bulk multiscale cancellation.
We supervise a differentiable surrogate with the fast, accurate SG oracle
instead — preserving every scientific objective (differentiable forward model,
inverse design, Bayesian UQ, active learning, calibration) while actually
working. Full diagnosis: [`../docs/forward_model_reframe.md`](../docs/forward_model_reframe.md).

## Colab persistence

After mounting Drive, write trained ensembles and figures to
`/content/drive/MyDrive/BayesPINN_Inv/` so they survive session timeouts. The
surrogate trains in seconds, so most notebooks re-train from scratch in well
under the free-Colab compute budget.
