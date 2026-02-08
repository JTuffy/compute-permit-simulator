# Makefile for Compute Permit Simulator

.PHONY: run viz heatmap solara lint format clean help

help:
	@echo "Available commands:"
	@echo "  make run       - Run the simulation (CLI)"
	@echo "  make viz       - Run the Solara interactive dashboard"
	@echo "  make heatmap   - Generate the Deterrence Heatmap"
	@echo "  make lint      - Run linters (ruff)"
	@echo "  make format    - Format code (ruff)"
	@echo "  make clean     - Remove artifacts (__pycache__, etc.)"

run:
	uv run main.py

viz: solara

solara:
	uv run solara run app.py

heatmap:
	uv run python -m compute_permit_sim.vis.heatmap

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	rm -rf __pycache__
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
