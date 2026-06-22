# Makefile for Compute Permit Simulator

.PHONY: run viz app heatmap solara lint format test check clean help

help:
	@echo "Available commands:"
	@echo "  make run           - Run the simulation once (all scenarios)"
	@echo "  make mc            - Monte Carlo: 100 runs per scenario, exports CSV + LaTeX table"
	@echo "  make sweep         - Sensitivity sweeps (pi_0 and collateral on minimal scenario)"
	@echo "  make paper-results - Regenerate ALL paper figures + tables (outputs/paper/)"
	@echo "  make paper-smoke   - Fast pipeline check with tiny seed counts"
	@echo "  make app           - Run the Solara interactive dashboard (alias: viz)"
	@echo "  make lint          - Run linters (ruff check)"
	@echo "  make format        - Format code (ruff format)"
	@echo "  make ruff          - Run both ruff check and ruff format"
	@echo "  make mypy          - Run type checker (mypy)"
	@echo "  make test          - Run tests (pytest)"
	@echo "  make check         - Run all checks (lint, format, mypy, test)"
	@echo "  make clean         - Remove artifacts (__pycache__, etc.)"

run:
	uv run main.py

mc:
	uv run main.py --monte-carlo 100

sweep:
	uv run main.py --sweep-file sweep_pi0_minimal.json
	uv run main.py --sweep-file sweep_collateral_minimal.json

list-sweeps:
	@echo "Available sweep files:"
	@ls scenarios/sweeps/*.json 2>/dev/null || echo "  (none)"

# Regenerates every figure and table in the manuscript from committed configs.
# Protocol (seed counts) lives in services/paper_pipeline.py and must match
# the paper's experimental-protocol subsection.
paper-results:
	uv run main.py --paper
	@echo "--- artifacts in outputs/paper/ ---"

paper-smoke:
	uv run main.py --paper --smoke

viz: solara

app: solara

solara:
	uv run solara run app.py


lint:
	uv run ruff check .

format:
	uv run ruff format .

ruff: format lint

mypy:
	uv run mypy .

test:
	uv run pytest -q

check: lint format mypy test

clean:
	rm -rf __pycache__
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
