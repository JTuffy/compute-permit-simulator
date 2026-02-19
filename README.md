# Compute Permit Market Simulator

> **A Multi-Agent Simulation of AI Compute Regulation, Compliance, and Deterrence.**

This project models the strategic interaction between **AI Labs** (seeking to maximize profit by training models) and an **Auditor** (seeking to enforce compute permit limits). It serves as a computational playground to explore the conditions under which regulation succeeds or fails.

[![Pipeline](https://gitlab.com/aisc-cm-simulator/badges/main/pipeline.svg)](https://gitlab.com/aisc-cm-simulator/pipelines)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Quick Start

The simulator provides an interactive web dashboard for real-time experimentation.

### Prerequisites

- Python 3.13+
- [uv](https://astral.sh/uv) (recommended for dependency management)

### Installation

```bash
# 1. Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and Sync
git clone https://gitlab.com/your-org/aisc-cm-simulator.git
cd aisc-cm-simulator
uv sync
```

## 🎮 Usage

### Interactive Dashboard
Launch the visualization dashboard to explore the model interactively.

```bash
uv run solara run app.py
```

**Key Features:**
- **Scenario Control**: Adjust penalty ($P$), detection prob ($p$), and audit capacity ($N$) on the fly.
- **Real-time Analysis**: Watch compliance rates and market prices evolve.
- **Agent Inspector**: Drill down into individual lab behaviors and audit history.

### CLI Simulation
Run headless simulations for bulk data collection.

```bash
uv run main.py
```

---

## 🛠️ Development

We use `uv` for all development tasks to ensure reproducibility.

| Task | Command |
|------|---------|
| **Run Tests** | `uv run pytest` |
| **Lint** | `uv run ruff check .` |
| **Type Check** | `uv run mypy .` |
| **Format** | `uv run ruff format .` |


### CI/CD Pipeline
This project includes a GitLab CI/CD pipeline that:
1.  **Tests**: Runs `pytest` on every commit.
2.  **Deploys**: Builds the Solara app (WASM) to GitLab Pages on merge to `main`.

---

## 📚 Documentation

For deep technical details on the architecture, decision logic, and mesa model structure, see:
👉 [**Technical Documentation**](TECHNICAL_DOCUMENTATION.md)

