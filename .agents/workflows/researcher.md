---
description: Researcher workflow — run parameter sweep experiments against the simulation, analyze results, and iterate toward interesting insights. Produces reproducible figures and a findings log.
---

# Researcher Workflow

Use this workflow when the goal is to **generate knowledge** from the simulation through
parameter sweeps — discover interesting compliance regimes, confirm or refute hypotheses,
and produce figures suitable for the paper.

> [!IMPORTANT]
> **Read `agent_workspace/research/synthesis.md` first** — this is the single source of
> truth for what is already known. Do not repeat experiments already answered there.

## Workspace Structure

```
agent_workspace/
├── sections/
│   └── <section_slug>/          # e.g. section_43
│       ├── explore_sweep.py     # thin-caller sweep runner — the main experiment tool
│       ├── findings.md          # running log of all experiments and verdicts
│       └── figures/
│           └── run_NNN/         # one folder per research session / batch of runs
│               ├── *.png        # generated sweep figures
│               └── params.json  # complete parameter + result record for every figure
└── research/
    └── synthesis.md             # cross-session synthesis (update with /synthesize-research)
```

**Run folder contract**: every invocation of `explore_sweep.py` either creates a new
`run_NNN/` folder (auto-incremented) or adds to an existing one (using `--run N`).
Each run folder contains the figures and a `params.json` that records every experiment
in that folder for reproducibility.

## Setup (first time in a repo)

1. Ensure the simulator installs cleanly:
   ```bash
   uv sync
   ```

2. Create the section folder and figures directory if they don't exist:
   ```bash
   mkdir -p agent_workspace/sections/<slug>/figures
   ```

3. Create `findings.md` in the section folder with this header:
   ```markdown
   # Sweep Findings Log

   | # | Scenario | Param | Range | n | Verdict | Notes | Figure |
   |---|---|---|---|---|---|---|---|
   ```

4. The sweep runner script `explore_sweep.py` must exist (copy from another section or
   create fresh — the pattern is documented below).

## Running an Experiment

```bash
uv run python agent_workspace/sections/<slug>/explore_sweep.py \
    --scenario basic/scenario_2_strict.json \
    --param market.fixed_price \
    --min 5 --max 200 --step 10 \
    --n-runs 30 \
    --out crisis_fixed_price.png \
    --ref "70|orange"          # optional: x-value|color for scenario default marker
```

Key flags:
| Flag | Required | Description |
|---|---|---|
| `--scenario` | ✓ | Path relative to `scenarios/`, e.g. `basic/scenario_2_strict.json` |
| `--param` | ✓ | Dot-path into `ScenarioConfig`, e.g. `market.fixed_price` |
| `--min/--max/--step` | ✓ | Value range for the sweep |
| `--n-runs` | | Monte Carlo replications per point (default: 30) |
| `--out` | ✓ | PNG filename, saved inside the current run folder |
| `--run N` | | Add to existing `run_N` instead of auto-incrementing |
| `--ref "X\|color"` | | Mark a scenario's default value on the curve (pipe-delimited; NO `$` in the arg — bash expands it) |

> [!CAUTION]
> Never use `$` in `--ref` labels. Bash expands `$70` to empty before Python sees it.
> The plotting code appends the x-value and scenario name automatically: `"Strict Enforcement default: 70"`.

## Interpreting Results

The script prints a `VERDICT` on exit:
- **INTERESTING**: compliance range > 20 pp OR max SD > 7 pp across the sweep
- **FLAT**: sweep produces no meaningful variation — move on

**What makes a sweep interesting for the paper:**
- Non-linear effect: knee, plateau, phase transition
- Tipping point where ≥ 95% compliance is first achieved or lost
- Wide compliance range (> 30 pp) with low SD (signal not noise)
- Result that contradicts an intuitive expectation

**What to skip:**
- Flat lines — even if mechanistically correct, they don't tell a visual story
- Sweeps where SD > mean × 0.5 — variance dominates, result is noise

## Tools Available

All are in `vis/plotting.py` — check there before writing any matplotlib:

```python
from compute_permit_sim.vis.plotting import plot_sweep_curve
from compute_permit_sim.services.sweep import run_sweep
from compute_permit_sim.services.config_manager import load_scenario
from compute_permit_sim.schemas.sweep_params import get_param, generate_values
```

`plot_sweep_curve(result, metric="avg_compliance", reference_lines=[(x, label, color)])`:
- Plots mean ± 1 SD band
- Annotates every 95% threshold crossing as "Tipping (95%) ≈ X"
- Marks scenario default values as diamonds on the curve, labelled with scenario name
- Reference line labels are ignored (label is auto-derived); only x-value and color matter

## Findings Log

After each experiment, add a row to `findings.md`:

```
| NN | Scenario | param.path | min–max | n_runs | FLAT/INTERESTING | one-line note | run_NNN/filename.png |
```

Keep the log as the source of truth for what has been run. The `params.json` in each
run folder is the reproducibility record; the findings log is the research narrative.

## Iteration Loop

1. **Hypothesise**: pick a scenario + parameter expected to show non-linear behaviour
2. **Run**: `explore_sweep.py --scenario ... --param ... --min ... --max ...`
3. **View**: read the PNG with `view_file` — check labels, tipping points, curve shape
4. **Judge**: INTERESTING (save, log, continue) or FLAT (note why, pick different param)
5. **Repeat** until you have 2–3 interesting curves per scenario for the paper

**Typical interesting dimensions per scenario type:**
- *High-price scenario* (e.g. Crisis): sweep `market.fixed_price` and `lab.economic_value_max`
- *Enforcement scenario* (e.g. Maxwell): sweep `audit.base_prob` and `audit.penalty_amount`
- *Supply-constrained* (e.g. Lawless): sweep `market.permit_cap`
- *Dynamic* (e.g. Dynamic Escalation): sweep `audit.audit_escalation`

## After the Session

Run `/synthesize-research` to merge findings into `agent_workspace/research/synthesis.md`.
