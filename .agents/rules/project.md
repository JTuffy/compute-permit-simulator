---
trigger: always_on
description: Project-specific conventions — design decisions and patterns specific to this codebase. Update when patterns change.
---

# rules/project.md

<!-- Project-specific only. Nothing in this file transfers to other projects.
     Entries should be understandable to an agent implementing a similar feature from scratch.
     Avoid exhaustive specifics — capture intent and known pitfalls. -->

## Architecture

Three-layer import hierarchy: `vis` → `services` → `schemas`. Lower layers never import upward. Shared state that crosses layers lives in a neutral singleton module.

Data shapes are defined in `schemas/` before logic is written. All schema models are immutable by default; use `model_copy(update={...})` for changes.

## Run State Pattern

All simulation modes (basic, Monte Carlo, sweep) share one generic `RunState[T]` in `vis/state/run_state.py`. Three module-level singletons — `basic_run`, `mc_run`, `sweep_run` — govern all run states.

Transition: idle → running → ready.

- Background worker computes everything; UI receives one complete result in one atomic `.set()` call
- Set result and `phase="ready"` together — never two calls
- When a basic run starts, clear `mc_run` and `sweep_run` to idle (and vice-versa for batch), so the page state machine always routes correctly
- When a history entry is selected via `view_run()`, clear batch RunState to idle so AnalysisPanel shows
- Solara hooks (`use_state`, `use_memo`) must be called unconditionally before any early `return`

## Page-Level State Machine (`vis/page.py`)

Right-pane rendering priority:
1. Any run phase `running` → `RunSpinner`
2. `mc_run` or `sweep_run` phase `ready` → `BatchResultsPanel`
3. `basic_run` phase `ready` OR `session_history.selected_run` set → `AnalysisPanel`
4. Else → `EmptyState`

This is the single source of truth for what the right pane displays.

## Reactive State

| Singleton | File | Purpose |
|---|---|---|
| `ui_config` | `vis/state/config.py` | Reactive scenario params (mirrors `ScenarioConfig`) |
| `basic_run` | `vis/state/run_state.py` | `RunState[SimulationRun]` for basic runs |
| `mc_run` | `vis/state/run_state.py` | `RunState[MonteCarloResult]` for Monte Carlo |
| `sweep_run` | `vis/state/run_state.py` | `RunState[SweepResult]` for parameter sweeps |
| `session_history` | `vis/state/history.py` | Run list + `scenario_name_map` |
| `engine` | `vis/state/engine.py` | `SimulationEngine` singleton |

`session_history.scenario_name_map` is `Reactive[dict[str, str]]` (display name → filename).
Use it in all dropdowns. Never call `list_scenarios()` directly in a UI component.

## Mirrored Schema Layers (UIConfig Pattern)

`UIConfig` in `vis/state/config.py` mirrors `ScenarioConfig` dynamically: it flattens
nested sub-model fields into reactive attributes via `_create_reactive_fields()`. A
`_reactive_field_names: frozenset[str]` registry is built at init and used for all
runtime lookups — never `hasattr(self, name)`. Unknown fields raise `KeyError` immediately.
`_SPECIAL_FIELDS` lists fields handled explicitly (seed, name, notes, description).

When adding a new `ScenarioConfig` field: run `uv run pytest tests/vis/` first — the
sync-guard test will catch any drift between the schema and UIConfig's reactive registry.

## Logging

All logging configuration lives in `vis/logging_config.py` (`configure_logging()`).
`page.py` calls it once at startup. Do not add logging setup anywhere else — Solara
reloads will re-run module-level code and accumulate duplicate handlers.

## UI Structure

Each feature area has a sidebar panel (configuration) and a right-pane panel (results). Results panels follow a three-section structure:
- `Card("Summary")` — metric chips row (left) + `ResultsActions` (right, bordered)
- `Card("Results")` — charts in `Columns([1, 1, 1])` with `ExpandableChart` + `DownloadPNG` per chart
- `Card("Statistics")` — markdown table

All shared result-display primitives (`MetricChip`, `ResultsActions`, `DownloadCSV/Excel/PNG/TeX/JSON`, `fig_to_png`) live in `vis/components/results.py`. Never re-implement these inline.

**All history entry types (`RunHistoryItem`, `BatchHistoryItem`, and any future type) must support the same set of actions.** Before implementing a new entry type, enumerate every action the richest existing type exposes and design for full parity from the start. Asymmetric feature sets cause visual inconsistency that is costly to fix after the fact.

## Batch Results and History

`MonteCarloResult` and `SweepResult` both carry an `id: str` (8-char UUID prefix) and `config: ScenarioConfig` (the base config used for the run). The `id` provides a stable short identifier; `config` enables the config dialog and save-as-template features. Both fields have defaults so existing call sites only need to pass `config=` explicitly in the service functions.

MC results are appended to `session_history.batch_results` after completion. Sweep results are stored there too (both types are `BatchResult = MonteCarloResult | SweepResult`). The run history (`session_history.run_history`) holds individual `SimulationRun` objects from basic runs only.

`BatchHistoryItem` intentionally mirrors `RunHistoryItem`'s row layout exactly: type-icon | ⓘ RunConfigDialog | id-label | save-template | Excel | CSV | JSON. The type icon (chart-bell vs trending-up) is the only visual distinction. Long labels truncate via `.run-history-compact .v-btn .v-btn__content` CSS rule.

## Scenario and Config Files

Scenario JSONs in `scenarios/basic/` — match `ScenarioConfig`. Required: `name`. Omitted fields use `DEFAULT_*` from `schemas/defaults.py`.

Sweep parameters registered in `schemas/sweep_params.py` as `SweepParam` entries. New sweepable parameters go there first, before any UI wiring.

## Exports (`vis/export.py`)

All export functions return `bytes` for Solara's `FileDownload`. Key functions:
`export_run_to_csv/excel`, `export_monte_carlo_to_csv/latex`, `export_mc_per_seed_to_csv` (requires `store_raw=True`), `export_mc_trajectory_to_csv`, `export_sweep_to_csv`.

## Plots (`vis/plotting.py`)

Accept typed result objects, return `matplotlib.Figure`, never import Solara. Use `fig_to_png(fig)` from `results.py` to convert to bytes for downloads. Standard figsize `(7, 4)`.

## Testing

Schema sync tests detect drift between the schema and any mirrored layer (e.g. UI config). These tests live in `tests/vis/` and must be updated when adding new schema fields. Complex model construction uses shared factories in `tests/factories.py`.

**Before removing a schema field:** grep `src/` and `tests/` for all references. Confirm the field is never populated or read. If the field is meant for future use but currently empty, remove it and re-add with a typed schema when the feature is scoped — `list[dict]` fields are not acceptable placeholders.

## Styling: Global vs. Scoped CSS

**Input field rules are globally scoped** in `style.css` — they target `.v-text-field` directly, not through `.sidebar-compact` or `.config-view`. This is intentional: Vuetify 2 underline/label bugs must be corrected everywhere, not just in known container classes.

**When adding new CSS:**
- Input field corrections (label float, underline, font) → global, no container selector
- Section headers (`v-subheader`) → global (only ever used in config contexts)
- Layout/density adjustments (card padding, tab sizing) → `.sidebar-compact` or `.config-view` scope is fine
- **Do not split** the same visual rule across both `.sidebar-compact` and `.config-view` — fix it globally and remove the duplication

The two-scope system (`.sidebar-compact` + `.config-view`) exists only for layout/density rules that genuinely differ between the sidebar and dialog contexts. Any rule that appears under both selectors with the same value should be promoted to global scope.

