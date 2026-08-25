# BayesPINN-Inv Makefile.
# Reproducible developer workflows.

.PHONY: help install dev test test-slow lint format clean smoke selftest \
        results identifiability train inverse al build check-install docs

PYTHON ?= python
PIP    ?= pip
SRC     = src/bayespinn_inv
TESTS   = tests

help:
	@echo "BayesPINN-Inv -- common targets"
	@echo
	@echo "  make install         Install package (no dev deps)"
	@echo "  make dev             Install with dev dependencies"
	@echo "  make test            Run the test suite (~40 s)"
	@echo "  make selftest        Physics self-check of the installed package"
	@echo "  make lint            ruff + mypy (ruff must exit 0)"
	@echo "  make format          Auto-format with black + ruff --fix"
	@echo
	@echo "  Experiments (each writes results + manifest.json to outputs/):"
	@echo "  make results         H1-H5 quantitative results   (~25 min)"
	@echo "  make identifiability Identifiability analysis     (~6 min)"
	@echo "  make identifiability-robustness   Is 3-5/16 robust? (~35 min)"
	@echo "  make uq-benchmark    Ensemble vs MC-dropout vs SWAG (~3 min)"
	@echo "  make uq-tuning       ... with a fair hyperparameter search (~10 min)"
	@echo "  make experiment-design  Information- vs uncertainty-driven bias choice"
	@echo "  make gradient-fidelity  Where are the surrogate gradients usable?"
	@echo "  make pinn-vs-surrogate  Evidence for ADR-0004 (~4 min)"
	@echo "  make notebooks       Regenerate the twelve notebooks"
	@echo
	@echo "  Legacy PINN pipeline (superseded as a forward model):"
	@echo "  make smoke           Tiny end-to-end smoke run"
	@echo "  make train           Full training (configs/train_base.yaml)"
	@echo "  make inverse         Inverse design (configs/inverse_base.yaml)"
	@echo "  make al              Active learning (configs/al_base.yaml)"
	@echo
	@echo "  make build           Build the wheel"
	@echo "  make check-install   Build, install into a clean venv, run tests there"
	@echo "  make clean           Remove build artifacts"

install:
	$(PIP) install -e .

dev:
	$(PIP) install -e ".[all]"

test:
	PYTHONPATH=src $(PYTHON) -m pytest $(TESTS) -q --tb=short

test-slow:
	PYTHONPATH=src $(PYTHON) -m pytest $(TESTS) -q --tb=short -m slow

selftest:
	PYTHONPATH=src $(PYTHON) -m bayespinn_inv.cli selftest

# ruff must pass; mypy is advisory for now (large pre-existing surface).
lint:
	$(PYTHON) -m ruff check $(SRC) $(TESTS) scripts
	-$(PYTHON) -m mypy $(SRC)

format:
	$(PYTHON) -m black $(SRC) $(TESTS) scripts
	$(PYTHON) -m ruff check --fix $(SRC) $(TESTS) scripts

results:
	PYTHONPATH=src $(PYTHON) scripts/run_results.py

identifiability:
	PYTHONPATH=src $(PYTHON) scripts/run_identifiability.py

# Is the 3-5 of 16 result robust? Sweeps parameterisation, bias sampling,
# solver grid, doping level, FD step; bootstraps over measured biases.
identifiability-robustness:
	PYTHONPATH=src $(PYTHON) scripts/run_identifiability_robustness.py

# ADR-0005: deep ensemble vs MC-dropout vs SWAG under one protocol.
uq-benchmark:
	PYTHONPATH=src $(PYTHON) scripts/run_uq_benchmark.py

# ... and the fair hyperparameter search that rules out a tuning failure.
uq-tuning:
	PYTHONPATH=src $(PYTHON) scripts/run_uq_tuning.py

# DES-01: information-based bias selection vs uncertainty vs random.
experiment-design:
	PYTHONPATH=src $(PYTHON) scripts/run_experiment_design.py

# GRAD-01: are the surrogate's gradients trustworthy, and where?
gradient-fidelity:
	PYTHONPATH=src $(PYTHON) scripts/run_gradient_fidelity.py

# ADR-0004: the evidence that the pure-physics PINN is not a forward model.
pinn-vs-surrogate:
	PYTHONPATH=src $(PYTHON) scripts/run_pinn_vs_surrogate.py

# Regenerate the twelve notebooks from their generator (does not execute them).
notebooks:
	$(PYTHON) scripts/build_notebooks.py

smoke:
	PYTHONPATH=src $(PYTHON) scripts/train.py --config configs/train_smoke.yaml

train:
	PYTHONPATH=src $(PYTHON) scripts/train.py --config configs/train_base.yaml

inverse:
	PYTHONPATH=src $(PYTHON) scripts/inverse_design.py --config configs/inverse_base.yaml

al:
	PYTHONPATH=src $(PYTHON) scripts/active_learning.py --config configs/al_base.yaml

build:
	$(PYTHON) -m build --wheel

# Gate I: the package must work when installed, not just from the checkout.
# A venv puts its executables in bin/ on POSIX and Scripts/ on Windows.
# Hard-coding bin/ made this target unrunnable on the platform the project's
# own manifests record as the one the results were produced on -- the same
# defect class as AUDIT_MASTER BUG-14.
VENV_BIN := $(shell $(PYTHON) -c "import sys; print('Scripts' if sys.platform=='win32' else 'bin')")

check-install: build
	rm -rf .cleanenv
	$(PYTHON) -m venv .cleanenv
	.cleanenv/$(VENV_BIN)/python -m pip install -q --upgrade pip
	.cleanenv/$(VENV_BIN)/python -m pip install -q dist/*.whl pytest
	.cleanenv/$(VENV_BIN)/bayespinn selftest
	.cleanenv/$(VENV_BIN)/python -m pytest $(TESTS) -q --tb=short

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info .cleanenv
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache

docs:
	@echo "docs/AUDIT_MASTER.md            -- every audit finding + evidence"
	@echo "docs/CLAIM_EVIDENCE_MATRIX.md   -- every claim -> reproducing command"
	@echo "docs/NOVELTY_AUDIT.md           -- prior art and scope of claims"
	@echo "docs/RELEASE_READINESS.md       -- release gates with evidence"
	@echo "docs/adr/                       -- architecture decision records"
