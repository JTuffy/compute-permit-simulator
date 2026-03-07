---
trigger: always_on
description: How to build a new feature — meta checklist for consistency, state design, and cross-feature review.
---

# Feature Building Workflow

Use before implementing any non-trivial feature.

## Before writing code

1. **Find existing analogues.** What features already do something similar? List them. Your feature must follow the same pattern — not invent a new one.

2. **Define state transitions explicitly.** Every feature that takes time has four states: idle → loading → ready → error. Write down what the user sees at each state *before* implementation. Pay special attention to the loading → ready boundary: content must exist before loading clears.

3. **Centralize first.** If the new feature shares behaviour with an existing one, extract the shared piece before building on top of it. Never implement the same concern twice with plans to unify later.

## During implementation

Build in dependency order: shared primitives → background logic → state wiring → UI layer.

## After implementation

Compare the feature against its analogues side-by-side. If anything diverges in behaviour or timing, fix it now. Update `project.md` if a new durable pattern was established.
