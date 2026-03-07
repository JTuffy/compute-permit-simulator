---
trigger: always_on
description: General coding conventions — language-agnostic principles for any codebase.
---

# rules/coding.md

<!-- Applies to all work regardless of language or framework. -->

## Core Principles

Think in terms of systems. Think about designing interfaces. Consider how those interfaces might be scaled or expanded before you start. Consider making things shared, general, and how it should be professionally designed.

**Single source of truth.** If a value, label, or behaviour is defined in more than one
place, there must be one canonical source (a constant, registry, or reactive). Before
adding a new definition, find the existing one.

**Rationale over description.** Non-obvious decisions — a deliberate sleep, a skipped
field, an exception to a pattern — MUST have a one-line comment explaining *why*,
not just *what*. Code describes what; comments explain why.

## Layering and Boundaries

Enforce strict one-way dependency layers. Lower layers must not import from higher layers.
Cross-layer singletons or shared state belong in a dedicated neutral module.
Use type-checking-only import guards when a hint-only reference would create a cycle.

## Change Discipline

- Before implementing, check whether a workflow or pattern already exists for this task.
- Change the minimum surface area. Refactor opportunistically only when the change is in
  scope and isolated.
- If the same fix or pattern appears in three or more places, extract it before continuing.

## Testing

- Tests mirror source layout: `tests/foo/test_bar.py` covers `src/foo/bar.py`.
- Tests that touch the filesystem use temporary directories and mocks — never real paths.
- Use shared factories or fixtures for complex object construction; never build them inline.
- Coverage percentage is not a goal. Target correctness of logic boundaries.

## Definition of Done

A task is done when:
- All automated checks pass (lint, types, tests)
- The change has been read as a whole for coherence — not just the diff
- Rule files and workflows have been reviewed per `constitution.md`

## Inline Styles and Visual Tokens (UI)

**`style.css` is the single source of truth for typography, color, spacing, and opacity.**
Python `style=` attributes are allowed *only* for structural flex properties that must
be set per-component (e.g. `flex: 1`, `justify-content: space-between`) and cannot be
expressed through a shared CSS class.

**Never hardcode color hex or RGBA in Python.** Express colors through Vuetify semantic
tokens (`color="primary"`, `color="error"`) or CSS classes. All hex values belong in
`style.css` `:root` variables.

**Extract repeated `style=` strings to named constants.** If the same layout string
appears in more than one Python file, create a named constant (e.g. in `vis/styles.py`
or `vis/components/results.py`) and reference it. Never duplicate a layout string.

**Use CSS utility classes instead of inline attributes for typography/state:**
- Section labels → `SidebarLabel(text)` from `results.py` (wrapper component)
- Hint/descriptor text → `SidebarHint(text)` from `results.py` (wrapper component)
- Inline error messages → wrap in `solara.Column(classes=["sidebar-error-text"])`
- Empty-state muted text → wrap in `solara.Column(classes=["sidebar-empty-text"])`

**`solara.Markdown` and `solara.Text` do not accept `classes=`.** Passing it causes a
runtime `TypeError`. Check a component's signature before using `classes=` or `style=`.
The wrapper components `SidebarLabel` and `SidebarHint` exist precisely to bridge this
gap — they apply the CSS class to a containing Column, not the Markdown itself.

**Shared UI behaviour belongs in shared components, not per-panel code.** PNG download
for charts belongs in `ExpandableChart(download_filename=...)`. Export buttons belong in
`ResultsActions`. Adding a new pattern in more than one panel = extract first.
