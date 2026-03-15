---
trigger: always_on
description: Top-level amendments — for high-level notes that don't fit in other rule files. Add entries here rather than modifying main.md.
---

# amendments.md

<!-- Add dated, signed entries below when a top-level note is warranted.
     Keep each entry short. This file should stay mostly empty. -->

## 2026-03-07 — One-off scripts live in scripts/ or agent_workspace/

When you write a helper or reference script (data exploration, migration, benchmark,
experiment runner), place it in one of two locations:

- **`scripts/`** — committed, reusable across sessions. Use when the script is worth
  preserving (e.g. a data transform that might be re-run, a batch runner used repeatedly).
- **`agent_workspace/`** — gitignored, ephemeral. Use for one-off investigation scripts
  you don't expect to reuse.

After writing a reusable script to `scripts/`, add a one-line note in the most relevant
rules file (usually `project.md` or a workflow) indicating the script exists and when
to reach for it. This prevents re-inventing scripts across sessions.

See `python.md` for tooling conventions (`uv run python scripts/...`).

## 2026-03-07 — Reflect: four rule gaps found and patched

Sessionfriction identified during prune-repo + cleanup work:

- `python.md` Tooling section had a stray `or pipenv directly` sentence (stale merge artifact). Fixed.
- `coding.md` Core Principles first line had multiple typos. Fixed.
- `project.md` was missing three patterns established this session:
  - **UIConfig mirror pattern** (`_reactive_field_names` registry + `_SPECIAL_FIELDS`)
  - **Logging config** (`vis/logging_config.py` is canonical; never configure in `page.py`)
  - **Schema field removal checklist** (grep callers, confirm never populated, no `list[dict]` placeholders)
- `python.md` sync-guard test bullet was vague. Expanded with the concrete pattern: compare `model_fields` against the reactive registry at test time.

## 2026-03-12 — Always use vis/plotting.py for paper figures

`vis/plotting.py` is the single source of truth for all chart functions. When generating
figures for papers, scripts, or exports, **always call functions from there** — never write
custom matplotlib from scratch in agent_workspace scripts.

Available functions to reach for first:
- `plot_sweep_curve(SweepResult)` — 1D sweep line chart with tipping point annotation
- `plot_mc_trajectory(MonteCarloResult)` — compliance over steps, mean ± SD
- `plot_mc_violator_trajectory`, `plot_mc_audit_trajectory`, `plot_mc_payoff_comparison`

If a needed figure type does not exist in `vis/plotting.py` (e.g. a 2D heatmap), **add it
there** following the `create_figure()` style, then use it from both the UI and scripts.
Do not create ad-hoc matplotlib code in agent_workspace when an equivalent function
already exists or could be added once and shared.

## 2026-03-14 — Reflect: plotting discipline and scripting infrastructure

Three friction sources identified, all patched this session:

1. **`project.md` Plots section was too sparse** — 2 lines with no function inventory.
   Replaced with the full table of all 12 public functions and a mandatory "check before
   writing any matplotlib" gate. The agent cannot now claim ignorance of what exists.

2. **`researcher.md` step 4 had zero mention of `vis/plotting.py`** — meaning every
   research visualisation session was allowed to invent ad-hoc matplotlib. Added an
   `[!IMPORTANT]` callout before the visualise step enforcing the same gate.

3. **No `/gen-figures` workflow existed** — figure generation for paper sections was
   improvised each time. Created `.agents/workflows/gen-figures.md` with a step-by-step
   thin-caller checklist, a copy-paste script template, and a `// turbo` run step.
   Also created `scripts/README.md` as the cross-session script index so existing
   scripts are discoverable rather than silently re-invented.
