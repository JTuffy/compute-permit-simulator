# Makefile for Compute Permit Simulator

.PHONY: run viz app heatmap solara lint format test check clean help

help:
	@echo "Available commands:"
	@echo "  make run       - Run the simulation (CLI)"
	@echo "  make app       - Run the Solara interactive dashboard (alias: viz)"
	@echo "  make lint      - Run linters (ruff check)"
	@echo "  make format    - Format code (ruff format)"
	@echo "  make ruff      - Run both ruff check and ruff format"
	@echo "  make mypy      - Run type checker (mypy)"
	@echo "  make test      - Run tests (pytest)"
	@echo "  make check     - Run all checks (lint, format, mypy, test)"
	@echo "  make clean     - Remove artifacts (__pycache__, etc.)"

run:
	uv run main.py

viz: solara

app: solara

solara:
	uv run solara run app.py

heatmap:
	uv run python -m compute_permit_sim.vis.heatmap

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
