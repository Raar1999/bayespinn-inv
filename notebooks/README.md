# Notebooks

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
| 03 | `03_sg_solver.ipynb` | The SG oracle: I–V over 13 orders of magnitude, ideality factor |
| 04 | `04_forward_surrogate.ipynb` | **The forward model** — SG-supervised surrogate, ~4% I–V error |
| 05 | `05_inverse_design.ipynb` | Recover doping from I–V by gradient descent through the surrogate |
| 06 | `06_mc_dropout.ipynb` | Uncertainty via MC-Dropout |
| 07 | `07_deep_ensemble.ipynb` | Uncertainty via deep ensemble |
| 08 | `08_active_learning.ipynb` | Which biases to measure — informativeness of high vs low bias |
| 09 | `09_calibration.ipynb` | Coverage diagnosis (overconfident) + temperature-scaling fix |
| 10 | `10_benchmarking.ipynb` | Accuracy + **~500× speed** vs SG |
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
