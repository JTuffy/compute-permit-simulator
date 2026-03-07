---
trigger: always_on
description: General coding conventions — language-agnostic principles for any codebase.
---

# rules/coding.md

<!-- Applies to all work regardless of language or framework. -->

## Core Principles

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
- Rule files and workflows have been reviewed per `main.md`