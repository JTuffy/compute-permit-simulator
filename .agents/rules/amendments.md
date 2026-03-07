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
