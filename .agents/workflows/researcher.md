---
description: Researcher workflow — run experiments against the simulation, analyze results, and iterate toward interesting insights. Mimics a domain researcher's scientific process.
---

# Researcher Workflow

Use this workflow when the goal is not to build software but to **generate knowledge**
about the simulation: discover interesting parameter regimes, confirm or refute
hypotheses, or produce results suitable for the paper.

The agent acts as a computational researcher. It forms a hypothesis, designs an
experiment, runs it, analyzes the output, **generates and evaluates figures**, updates
its understanding, and iterates.

## Workspace

All research artifacts live in `agent_workspace/` (gitignored, Docker-excluded):

```
agent_workspace/
├── scripts/          # reusable helpers — kept across sessions
│   ├── analyze_scenarios.py   # run canonical scenarios, print metrics
│   └── collect_code.py        # dump codebase to text for LLM context
└── research/         # one subfolder per research session
    └── YYYY-MM-DD_slug/       # e.g. 2026-03-07_audit-tipping-point
        ├── exp1_<name>.py     # experiment scripts
        ├── exp2_<name>.py
        ├── findings.md        # this session's findings (canonical output)
        ├── *.png              # figures saved by experiment scripts
        └── scenarios/         # draft scenario JSONs for this session
            └── *.json
```

**Session folder contract** — every researcher workflow invocation produces:
1. `findings.md` — hypothesis, result, interpretation, next steps
2. At least one experiment script (`exp<n>_<name>.py`) that is re-runnable
3. Any generated figures (`.png`) from matplotlib
4. Draft scenario JSONs scoped under `scenarios/` if new configs were explored

**Never write to `outputs/`** — that's the user's UI export directory.
Research outputs go under `agent_workspace/research/<session>/`.

## Setup

Before running experiments, orient yourself:

1. **Read `agent_workspace/research/synthesis.md`** first — this is the single source
   of truth for what is already known. It tells you what has been confirmed, what the
   interesting regime is, and which open questions remain. Do not repeat experiments
   that are already answered there.

2. **Check the previous session folder** (`agent_workspace/research/*/findings.md`)
   for the most recent raw findings, in case the synthesis hasn't been updated yet.

3. **Load the default scenario** as your baseline. All experiments should be expressed
   as deltas from it so results are comparable.

   > [!IMPORTANT]
   > The **default `ScenarioConfig` is degenerate** (100% compliance). More broadly,
   > **any config where `permit_cap ≥ n_agents` is degenerate** — agents can always
   > obtain a permit, so compliance costs nothing regardless of enforcement parameters.
   > The interesting regime is **`permit_cap < n_agents`** (forced scarcity). Compliance
   > tracks the Q/N ratio approximately linearly: `avg_compliance ≈ cap / n_agents`.
   > Always start from `research_margin_baseline.json` with a tightened cap (e.g. cap=10,
   > n_agents=15) as the canonical interesting starting point.
   >
   > **`detection_rate_given_audit = nan` is a diagnostic signal**, not missing data. It means zero
   > violations occurred — which confirms a degenerate config. Treat it as a hard
   > signal to rethink the parameter regime, not as an experiment result.

4. **Check the service API** — experiments call services directly (no Solara dependency):
   ```python
   from compute_permit_sim.services.simulation_runner import run_single
   from compute_permit_sim.services.monte_carlo import run_monte_carlo
   from compute_permit_sim.services.sweep import run_sweep
   from compute_permit_sim.schemas import ScenarioConfig
   ```

5. **Scenario file lifecycle:**
   - During research: write to `agent_workspace/research/scenarios/`
   - When finalized and validated: promote to `scenarios/basic/` with a clear, non-`research_` name
   - Never write draft scenario files to `scenarios/basic/` — that directory is for user-facing configs


## Service API Reference

All services are pure Python with no Solara dependency. Call them directly in experiment scripts.

### Basic run — `run_single`
```python
from compute_permit_sim.services.simulation_runner import run_single
from compute_permit_sim.schemas import ScenarioConfig

result = run_single(config)  # returns SimulationRun
print(result.metrics.avg_compliance)
print(result.metrics.final_compliance)
print(result.metrics.detection_rate_given_audit)
```

### Monte Carlo — `run_monte_carlo`
```python
from compute_permit_sim.services.monte_carlo import run_monte_carlo

result = run_monte_carlo(
    config=cfg,
    n_runs=30,          # replications
    store_raw=True,     # include per-seed rows in result.raw_seeds
    seeds=[0..n-1],     # optional: explicit seed list
)
# Key fields:
# result.avg_compliance.mean / .std
# result.final_compliance.mean / .std
# result.p10_compliance, result.p90_compliance
# result.pct_runs_full_compliance
# result.detection_rate_given_audit.mean
# result.step_compliance   — list[MetricStats], one per step
# result.raw_seeds         — list[SeedResult] if store_raw=True
```

### Parameter sweep — `run_sweep`
```python
from compute_permit_sim.services.sweep import run_sweep

result = run_sweep(
    base_config=cfg,
    param_path="audit.base_prob",      # dot-path into ScenarioConfig
    values=[0.02, 0.05, 0.10, 0.20],  # explicit value list
    param_label="Base Audit Rate π₀", # optional, for display/export
    n_runs=20,
)
# result.points — list[SweepPoint], each has .param_value + .result (MonteCarloResult)
for pt in result.points:
    print(pt.param_value, pt.result.avg_compliance.mean)
```

To generate a sweep value range from param registry defaults:
```python
from compute_permit_sim.schemas.sweep_params import get_param, generate_values
param = get_param("audit.base_prob")
values = generate_values(param, min_val=0.02, max_val=0.30, step=0.02)
```

### Loading scenario files
```python
from compute_permit_sim.services.config_manager import load_scenario

# From scenarios/basic/ (committed):
cfg = load_scenario("basic/scenario_2_strict.json")

# From agent_workspace (use absolute path):
from pathlib import Path
cfg = load_scenario(str(Path("agent_workspace/research/2026-03-07_audit-tipping-point/scenarios/research_margin_baseline.json")))
```

### Inline config construction + overrides
```python
from compute_permit_sim.schemas import ScenarioConfig

# Inline — good for one-off experiments:
cfg = ScenarioConfig(name="My Test", steps=60, n_agents=15)

# Override one field on a loaded scenario (frozen model):
from compute_permit_sim.schemas.sweep_params import override_config
cfg2 = override_config(cfg, "audit.base_prob", 0.12)
```


Each iteration is one experiment. Aim for 3–5 iterations before synthesising conclusions.

### 1 — Hypothesise

State a falsifiable hypothesis in plain English, e.g.:
> "Increasing `audit.base_prob` beyond 0.15 produces diminishing compliance returns
>  regardless of `collateral_amount`."

A good hypothesis:
- Names the mechanism it expects to activate
- Predicts the direction and rough magnitude of an effect
- Is refutable by the numbers you will produce

### 2 — Design

Choose the right experiment type:

| Goal | Tool |
|---|---|
| Point-in-time result for one config | `run_single` |
| Distribution of outcomes across seeds | `run_monte_carlo` (N ≥ 30) |
| How one parameter shifts compliance | `run_sweep` |

Write the script in `agent_workspace/research/exp_<n>_<short_name>.py`.

### 3 — Run and observe

```bash
uv run python agent_workspace/research/exp_1_baseline.py
```

- Note anomalies: did anything behave unexpectedly? Runtime? NaN values?
- Jot raw numbers as inline comments in the script before moving to analysis.

### 4 — Visualise and evaluate

After getting numeric results, generate figures. Ask yourself:

**Is this graph interesting?**
- Does it show a non-linear effect? (knee, saturation, phase transition)
- Does it contradict the expected direction?
- Does variance dominate? (if SD > mean × 0.5 the result is noise — don't graph it)
- Would a policy-maker care about the magnitude?

**If visually boring** (flat line, constant slope, trivial intercept), skip saving it
and iterate the hypothesis. An uninteresting result is useful information — note it.

**If promising**, save the PNG to `agent_workspace/research/` and use `generate_image`
to visualise what an ideal version of that graph would look like (different color scheme,
better annotations, additional reference lines) — then iterate toward it in matplotlib.

### 5 — Analyse

- Compute the effect size relative to baseline (% change, not just absolute).
- Check whether variance swamps the signal: if SD > mean × 0.5, the result is noise.
- Look for non-linearities: does the curve have a knee? Is there a saturation point?
- Cross-reference against `SweepResult.tipping_point()` if applicable.

### 6 — Update understanding and iterate

- Re-state whether the hypothesis was confirmed, refuted, or inconclusive.
- Refine the next hypothesis based on what surprised you.
- Stop when you have confident results across ≥ 2 related dimensions,
  or when the last two iterations produce no new insight.

## Synthesis

After the loop, produce a markdown summary saved to `agent_workspace/research/findings_<date>.md`:

- One paragraph per experiment: hypothesis → result → interpretation
- A table of key numeric findings
- Recommended parameter ranges for the paper's figures
- Any caveats (e.g. sensitivity to `n_runs`, boundary effects)
- Embed the most interesting figures as images

## Notes on scale

- Monte Carlo with `n_runs=50` takes ~10–30 s for 100 steps.
- Sweeps over 10+ points with `n_runs=20` each can take several minutes.
- For quick orientation experiments, use `n_runs=10` and `steps=50`; scale up to
  confirm final results.
- All services are pure Python with no Solara dependency — safe to call headlessly.
