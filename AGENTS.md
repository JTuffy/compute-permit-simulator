# AGENTS.md -- Compute Permit Simulator

<!-- Machine-readable first. Primary instruction set for AI agents and human developers.
     MUST / SHOULD / NEVER used throughout as defined below. -->

---

## Part 1 -- Meta

### Purpose and Living Document Rule

This file captures patterns and constraints not inferrable from code alone.
Keep rules terse. Numbered sections support stable cross-references.

**Self-review requirement (stable — rarely changes):**
Before closing any task, ask: *should AGENTS.md be updated?*
Update sparingly — only when a new pattern is established or an existing rule proved wrong.
Do not add noise; a bloated AGENTS.md is as harmful as a stale one.

---

## Part 2 -- Python / Project Conventions

### Tooling

Use `uv` exclusively for all Python operations.

```
uv sync                          # install dependencies
uv add <pkg> / uv add --dev <pkg>
uv run python ...                # always via uv
uv run pytest -q                 # tests
uv run ruff check . --fix        # lint
uv run ruff format .             # format
uv run mypy .                    # types
```

Make targets (`make test`, `make check`, etc.) wrap these but may not work in all environments.
When in doubt, use `uv run` directly.

**Definition of done:** code works + `uv run pytest -q` passes + `uv run ruff check .` clean
+ `uv run mypy .` clean + AGENTS.md self-review complete.

### Schema-First Workflow

1. Schema first -- define data shapes before wiring them into logic or UI
2. State/UI -- expose reactively if needed
3. Logic -- implement in services
4. Test -- sync/drift guard tests auto-detect when layers fall out of step
5. Verify -- full check suite

### Code Patterns

- NEVER use `getattr(obj, "string")` on typed objects -- use typed attribute access.
- Replace `assert isinstance(x, T)` with `raise TypeError(...)` in production paths.
- Batch reactive state updates into one call rather than N sequential assignments.
- Heavy side-effects in Solara: use `use_task`. NEVER block in `use_effect`.

### General Design Principles

**Single source of truth.** If a value appears in 2+ places, there must be one canonical
source (reactive, constant, registry). Find it before creating a new one.

**Naming conventions.** Keep them consistent and predictable within the codebase.
Document the project's specific naming patterns in Part 3 -- not here.

**Rationale in code.** Non-obvious choices MUST have a one-line comment explaining *why*.

## Part 3 -- Domain Knowledge

### What It Does

Agent-based compute permit market. Labs decide each step: comply (fee + collateral + audits)
or violate (no permit). Regulator audits and penalizes. N steps, tracks compliance dynamics.

Key levers: `audit.base_prob` (pi0), `collateral_amount`, `audit.penalty_amount`,
`lab.risk_profile`, `market.permit_cap`. All higher -> more deterrence (except risk_profile).

### Running It

```bash
make app            # Solara interactive UI (primary)
make run            # CLI: all scenarios once
make mc             # CLI: Monte Carlo, 50 seeds
make sweep          # CLI: sweep from JSON file
make paper-results  # mc + sweep + print LaTeX
```

### Scenario and Sweep Files

Scenario JSONs in `scenarios/basic/` -- match `ScenarioConfig`. Required: `name`.
Optional: `notes` (shown as italic preview in LoadScenarioDialog).
Omitted fields use `DEFAULT_*` from `schemas/defaults.py`.

Sweep JSONs in `scenarios/sweeps/` -- use `min_val`/`max_val`/`interval` (NOT `values`).
`param_path` is a dot-path into `ScenarioConfig` (e.g. `"audit.base_prob"`).
New sweepable params go in `schemas/sweep_params.py` as `SweepParam` entries.

### Reactive State

| Singleton | File | Purpose |
|---|---|---|
| `ui_config` | `vis/state/config.py` | Reactive scenario params |
| `active_sim` | `vis/state/active.py` | Live run state (one Pydantic model in one reactive) |
| `session_history` | `vis/state/history.py` | Run list + `scenario_name_map` |
| `engine` | `vis/state/engine.py` | SimulationEngine singleton |
| `batch_mode`, `mc_result`, `sweep_result` | `vis/panels/batch.py` | Batch results reactive |

`active_sim.update(**kwargs)` = one `model_copy()` = one re-render. NEVER assign fields directly.
`session_history.scenario_name_map` is `Reactive[dict[str, str]]` (display name -> filename).
MUST use it in all dropdowns. NEVER call `list_scenarios()` in a UI component.

### Batch Analysis

Both MC and sweep run in `threading.Thread(daemon=True)`, update module-level reactives on done.
Results pane observes and re-renders once. `store_raw=True` on MC captures per-seed data.

### Exports (`vis/export.py`)

All return `bytes` for `FileDownload`. Key functions:
`export_run_to_csv/excel`, `export_monte_carlo_to_csv/latex`,
`export_mc_per_seed_to_csv` (needs `store_raw=True`), `export_mc_trajectory_to_csv`,
`export_sweep_to_csv`.

### UI Patterns

**Metric chips** -- `_MetricChip(label, value)` renders `**label:** value`.
Use in `solara.Row(style="gap: 24px; flex-wrap: wrap; flex: 1;")`.

**Icon-only downloads** -- wrap `FileDownload` in `Tooltip` + icon `Button`. NEVER use text labels.
Icons: `mdi-file-delimited-outline` (CSV), `mdi-file-excel-outline` (Excel),
`mdi-file-image-outline` (PNG), `mdi-code-braces` (LaTeX).

**Three-card results layout** (used by both `analysis.py` and `batch_results.py`):
`"Summary"` = metric chips + download buttons | `"Results"` = charts | `"Statistics"` = table.

**Plots** (`vis/plotting.py`): accept typed result objects, return `Figure`, never import Solara.
Standard figsize `(7, 4)`. Caller converts to PNG bytes via `io.BytesIO`.

### Performance Notes

Basic runs step-by-step with `asyncio.sleep(0.05)` per step + full re-render each step.
Batch runs headlessly in one thread -- zero per-step renders, one update on completion.
This is why batch appears much faster; it is not a bug in basic.

Future: refactor basic to headless background runner sharing `_run_single_seed(config)`
with `run_monte_carlo`, rendering results all at once after completion.
