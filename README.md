# Compute Permit Market Simulator

> **A Multi-Agent Simulation of AI Compute Regulation, Compliance, and Deterrence.**

This project models the strategic interaction between **AI Labs** (seeking to maximize profit by training models) and an **Auditor** (seeking to enforce compute permit limits). It serves as a computational playground to explore the conditions under which regulation succeeds or fails.

[![Pipeline](https://gitlab.com/aisc-cm-simulator/badges/main/pipeline.svg)](https://gitlab.com/aisc-cm-simulator/pipelines)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Quick Start

```bash
# 1. Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and sync dependencies
git clone https://gitlab.com/your-org/aisc-cm-simulator.git
cd aisc-cm-simulator
uv sync

# 3. Launch the interactive dashboard
make app
```

## 🎮 Usage

### Interactive Dashboard

```bash
make app            # Solara web UI (primary interface)
```

The UI provides three modes:
- **Simulate** tab — configure and run a single scenario, view results with step-by-step explorer
- **Batch** tab — Monte Carlo across many seeds, or parameter sweep across a range
- **Run History** — accessible from either tab; click any historical run to load its results

### CLI Simulation

```bash
make run            # CLI: run all scenarios once
make mc             # CLI: Monte Carlo, 50 seeds
make sweep          # CLI: parameter sweep from JSON file
make paper-results  # mc + sweep + print LaTeX
```

### Key Parameters

| Parameter | Symbol | Effect |
|---|---|---|
| `audit.base_prob` | π₀ | Baseline audit probability — higher → more deterrence |
| `collateral_amount` | — | Upfront collateral at stake — higher → more deterrence |
| `audit.penalty_amount` | — | Fine for caught violators — higher → more deterrence |
| `lab.risk_profile` | — | Lab risk tolerance — higher → less deterrence |
| `market.permit_cap` | — | Permit supply ceiling |

## 🛠️ Development

```bash
uv run pytest -q          # run tests
uv run ruff check . --fix # lint (auto-fix)
uv run ruff format .      # format
uv run mypy .             # type check
```

### Project Structure

```
src/compute_permit_sim/
├── schemas/         # Data models (SimulationRun, ScenarioConfig, …)
├── services/        # Simulation logic, Monte Carlo, sweep, exports
└── vis/             # Solara UI
    ├── panels/      # Sidebar + results panels
    ├── components/  # Shared UI primitives (results.py, history.py, …)
    └── state/       # Reactive singletons (run_state.py, history.py, …)
scenarios/
├── basic/           # Scenario JSON files (match ScenarioConfig)
└── sweeps/          # Sweep config JSON files
```

### CI/CD Pipeline

GitLab CI runs `pytest`, `ruff`, and `mypy` on every commit and deploys the Solara app to GitLab Pages on merge to `main`.

---

## 📚 Documentation

For deep technical details on the architecture and mesa model structure, see:
👉 [**Technical Documentation**](TECHNICAL_DOCUMENTATION.md)
