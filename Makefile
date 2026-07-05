# BayesPINN-Inv Makefile.
# Reproducible developer workflows.

.PHONY: help install dev test test-slow lint format clean smoke train inverse al docs

PYTHON ?= python
PIP    ?= pip
SRC     = src/bayespinn_inv
TESTS   = tests

help:
	@echo "BayesPINN-Inv -- common targets"
	@echo
	@echo "  make install      Install package (no dev deps)"
	@echo "  make dev          Install with dev dependencies"
	@echo "  make test         Run fast unit tests (~10s)"
	@echo "  make test-slow    Run integration tests (training, ~minutes)"
	@echo "  make lint         Run ruff lint checks"
	@echo "  make format       Auto-format with black + ruff --fix"
	@echo "  make smoke        Tiny end-to-end smoke run (1 ensemble member, 200 epochs)"
	@echo "  make train        Full training run (configs/train_base.yaml)"
	@echo "  make inverse      Inverse design (configs/inverse_base.yaml)"
	@echo "  make al           Active learning experiments (configs/al_base.yaml)"
	@echo "  make clean        Remove build artifacts"

install:
	$(PIP) install -e .

dev:
	$(PIP) install -e ".[all]"

test:
	PYTHONPATH=src $(PYTHON) -m pytest $(TESTS) -q --tb=short -m "not slow"

test-slow:
	PYTHONPATH=src $(PYTHON) -m pytest $(TESTS) -q --tb=short -m slow

lint:
	$(PYTHON) -m ruff check $(SRC) $(TESTS) scripts || true
	$(PYTHON) -m mypy $(SRC)   || true

format:
	$(PYTHON) -m black $(SRC) $(TESTS) scripts
	$(PYTHON) -m ruff check --fix $(SRC) $(TESTS) scripts

smoke:
	PYTHONPATH=src $(PYTHON) scripts/train.py --config configs/train_smoke.yaml

train:
	PYTHONPATH=src $(PYTHON) scripts/train.py --config configs/train_base.yaml

inverse:
	PYTHONPATH=src $(PYTHON) scripts/inverse_design.py --config configs/inverse_base.yaml

al:
	PYTHONPATH=src $(PYTHON) scripts/active_learning.py --config configs/al_base.yaml

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache

docs:
	@echo "Documentation is in docs/. Build with mkdocs / sphinx as desired."
