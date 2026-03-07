---
description: Researcher workflow — run experiments against the simulation, analyze results, and iterate toward interesting insights. Mimics a domain researcher's scientific process.
---

# Researcher Workflow

Use this workflow when the goal is not to build software but to **generate knowledge**
about the simulation: discover interesting parameter regimes, confirm or refute
hypotheses, or produce results suitable for the paper.

The agent acts as a computational researcher. It forms a hypothesis, designs an
experiment, runs it, analyzes the output, updates its understanding, and iterates.

## Setup

Before running experiments, orient yourself:

1. **Read `parameter_reference.md`** (if it exists in `docs/`) to understand each
   parameter, its default, and its expected sensitivity range.

2. **Read `README.md`** CLI section for the exact service call signatures:
   ```
   uv run python -m compute_permit_sim.cli run ...
   uv run python -m compute_permit_sim.cli monte-carlo ...
   uv run python -m compute_permit_sim.cli sweep ...
   ```

3. **Load the default scenario** as your baseline. All experiments should be expressed
   as deltas from it so results are comparable.

4. **Create `agent_workspace/research/`** (gitignored) for all output files.
   Never write experiment outputs to `outputs/` root — they will clash with UI exports.

## Experiment loop

Each iteration of the loop is one experiment. Aim for 3–5 iterations before
synthesising conclusions.

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
| Point-in-time result for one config | `run_single` (or basic CLI run) |
| Distribution of outcomes across seeds | `run_monte_carlo` (N ≥ 30) |
| How one parameter shifts compliance | `run_sweep` |

Write a Python script in `agent_workspace/research/exp_<n>_<short_name>.py` that
calls the services directly:

### 3 — Run and observe

- Run the script, capture stdout and any saved files.
- Note anomalies: did anything behave unexpectedly? Runtime? NaN values?
- Jot raw numbers as inline comments in the script before moving to analysis.

### 4 — Analyse

For numeric results:
- Compute the effect size relative to baseline (% change, not just absolute).
- Check whether variance swamps the signal: if SD > mean * 0.5, the result is noise.
- Look for non-linearities: does the curve have a knee? Is there a saturation point?
- Cross-reference against the `tipping_point()` method on `SweepResult` if applicable.

For unexpected results, ask:
- Is this a model property or a numerical artifact?
- Does reducing `n_runs` change the conclusion? (If yes, you need more seeds.)

### 5 — Update understanding and iterate

- Re-state whether the hypothesis was confirmed, refuted, or inconclusive.
- Refine the next hypothesis based on what surprised you.
- Update your experiment script or write a new one.
- Stop when you have confident results across ≥ 2 related dimensions,
  or when the last two iterations produce no new insight.

## Synthesis

After the loop, produce a brief markdown summary:
- One paragraph per experiment: hypothesis → result → interpretation
- A table of key numeric findings
- Recommended parameter ranges for the paper's figures
- Any caveats (e.g. sensitivity to `n_runs`, boundary effects)

Save the summary to `agent_workspace/research/findings_<date>.md`.

## Notes on scale

- Monte Carlo with `n_runs=50` takes ~10–30 s for 100 steps.
- Sweeps over 10+ points with `n_runs=20` each can take several minutes.
- For quick orientation experiments, use `n_runs=10` and `steps=50`; scale up to
  confirm final results.
- All services are pure Python with no Solara dependency — safe to call headlessly
  or from Docker.