# Makefile for Compute Permit Simulator

.PHONY: run viz app heatmap solara lint format test check clean help

help:
	@echo "Available commands:"
	@echo "  make run           - Run the simulation once (all scenarios)"
	@echo "  make mc            - Monte Carlo: 50 runs per scenario, exports CSV + LaTeX table"
	@echo "  make sweep         - Sensitivity sweep: π₀ on Lawless scenario"
	@echo "  make paper-results - Run MC + sweep and print LaTeX table to stdout"
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
	uv run main.py --monte-carlo 50

sweep:
	uv run main.py --sweep-file sweep_pi0_lawless.json
	uv run main.py --sweep-file sweep_collateral_lawless.json

list-sweeps:
	@echo "Available sweep files:"
	@ls scenarios/sweeps/*.json 2>/dev/null || echo "  (none)"

paper-results: mc sweep
	@echo "--- LaTeX table ---"
	@cat outputs/monte_carlo_table.tex

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
