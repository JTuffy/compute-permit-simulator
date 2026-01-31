# Compute Permit Market Simulator

A simulation of an AI Compute Permit Market, modeling the interactions between **AI Labs** (Firms) and a **Governor** (Regulator) in an environment with audit mechanisms and penalties.

## Overview

This project simulates a market for "compute permits" where:
1.  **Labs** decide whether to comply (buy permits) or defect (train without permits) based on their value, costs, and the expected penalty of being caught.
2.  **Market** determines the clearing price for permits based on aggregate demand.
3.  **Governor** monitors for signals of non-compliance and launches targeted audits ($pi_1$) or random audits ($pi_0$) to enforce the cap.

The simulation explores the **Deterrence Model**: under what conditions (Penalty $P$, Detection Probability $p$) do rational agents choose compliance?

## Installation

This project uses `uv` for dependency management.

1.  **Install `uv`** (if not already installed):
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Sync Dependencies**:
    ```bash
    uv sync
    ```

## Usage

### Command Line Simulation
Run the standard scenarios (Baseline, High Deterrence, Targeted Audit) defined in `scenarios/config.json`:

```bash
uv run main.py
# OR using make
make run
```

### Interactive Dashboard (Solara)
Launch the web-based interactive dashboard to adjust parameters ($P$, $p$, $Q$, $N$) in real-time and visualize Compliance/Price trends:

```bash
uv run solara run src/compute_permit_sim/vis/solara_app.py
# OR using make
make viz
```

### Deterrence Heatmap
Generate a static heatmap showing Compliance Rate across a grid of Penalty vs. Detection Probability:

```bash
uv run src/compute_permit_sim/vis/heatmap.py
# OR using make
make heatmap
```
*Output saved to `deterrence_heatmap.png`.*

## Project Structure

```text
src/compute_permit_sim/
├── domain/                    # core business logic
│   ├── agents.py              # Lab compliance logic (decision rule)
│   ├── market.py              # Permit market clearing mechanism
│   └── enforcement.py         # Governor audit & signal logic
├── infrastructure/            # simulation framework
│   ├── model.py               # Mesa model & step scheduler
│   └── data_collect.py        # Metrics collection
├── vis/                       # visualization
│   ├── solara_app.py          # Interactive dashboard
│   └── heatmap.py             # Static diagrams
└── schemas.py                 # Pydantic configuration models
```

## Development

We enforce strict code quality using `ruff`.

-   **Lint**: `make lint` or `uv run ruff check`
-   **Format**: `make format` or `uv run ruff format`

### Pre-commit Hooks

To automatically run linting and formatting on every commit:

```bash
uv run pre-commit install
```

To run checks manually on all files:

```bash
uv run pre-commit run --all-files
```

## Key Concepts

-   **Decision Rule**: Labs run without a permit if $v_i - c > E[Penalty]$.
-   **Expected Penalty**: $P \times p_{eff}$, where effective detection depends on Governor's signal quality ($\alpha, \beta$) and audit strategy.
-   **Scenarios**:
    1.  **Baseline**: Low enforcement.
    2.  **High Deterrence**: High penalties.
    3.  **The Signal** (Targeted Auditing): Using signals to target audits efficiently.
