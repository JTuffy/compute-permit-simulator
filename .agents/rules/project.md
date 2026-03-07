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

All simulation modes (basic, Monte Carlo, sweep) share the same state transition: idle → loading → ready. The rules:

- Background worker computes everything; UI receives one complete result
- Set the result reactive *before* clearing the running flag — the spinner should never clear into an absent-result state
- Both right-pane panels gate on a running flag at the top: when running, render only the shared `RunSpinner` component and return. This is the single source of truth for the loading experience.
- Solara hooks (`use_state`, `use_memo`) must be called unconditionally before any early `return` — even when the early return path is the common case

## UI Structure

Each feature area has a sidebar panel (configuration) and a right-pane panel (results). Results panels follow a three-section structure: summary metrics with download actions → charts → statistics table.

Download actions are icon-only, tooltip-labelled. Metric summary chips use a consistent inline row layout.

## Reactive State

Each major concern has one singleton reactive that owns its state. State is updated atomically — one call, one re-render. Singletons are not passed as props; components import them directly.

## Testing

Schema sync tests detect drift between the schema and any mirrored layer (e.g. UI config). These tests live in `tests/vis/` and must be updated when adding new schema fields. Complex model construction uses shared factories in `tests/factories.py`.
