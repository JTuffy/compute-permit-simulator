---
description: Synthesize research — merge findings from one or more session folders into the living synthesis document. Run after every researcher session.
---

# Synthesize Research Workflow

Use this workflow after completing a `/researcher` session, or at the start of a new
session when previous findings exist. It keeps `agent_workspace/research/synthesis.md`
current — the single source of truth for what is known about the simulation.

## When to run

- After any `/researcher` session produces a new `findings.md`
- When a previous session's results need to be refined or reinterpreted
- At the start of a new research planning phase, to inventory what's already known

## Inputs

All session `findings.md` files under `agent_workspace/research/*/findings.md`.
The current `synthesis.md` (if it exists).

## Output

An updated `agent_workspace/research/synthesis.md` that:
1. Incorporates all new empirical findings (tables, numbers, effect directions)
2. Promotes confirmed findings to the "What Has Been Tested" table
3. Removes or downgrades open questions that have been answered
4. Adds newly surfaced open questions
5. Updates the Session Index with the new session entry
6. Restructures any section that has grown unwieldy or contains stale information

## Steps

### 1 — Read existing synthesis

```
view_file agent_workspace/research/synthesis.md
```

Note what is already covered. Identify which sections will need updating.

### 2 — Read new session findings

For each new `findings.md` not yet in the Session Index:

```
view_file agent_workspace/research/<session>/findings.md
```

Extract:
- **Confirmed findings** → add/update empirical numbers table and "What Has Been Tested"
- **Refuted hypotheses** → update open questions (remove or add a ⚠️ caveat)
- **Newly surfaced questions** → add to Open Research Questions with priority
- **Process observations** → update Section 7 (Process Knowledge) if new patterns emerged
- **Key numeric results** → add to Section 6 (Key Empirical Numbers)

### 3 — Merge into synthesis.md

Edit `synthesis.md` directly. Rules:

- **Do not simply append session summaries.** Synthesize — merge findings into the
  appropriate section, restructure when a section has grown, consolidate duplicates.
- **Precision over verbosity.** A row in a table beats a paragraph. A number beats a trend word.
- **Promote when confirmed.** A finding that has been reproduced in ≥ 2 sessions or
  under ≥ 2 parameter regimes is confirmed — move it from "Open" to "Tested/Known".
- **Retire stale open questions.** If answered, remove from the open questions table or
  mark with ✅. Do not let the open questions list grow unboundedly.
- **Restructure proactively.** If a section exceeds ~20 rows or ~400 words, split it
  by theme or introduce a summary + detail structure.

### 4 — Add session to index

Append a row to Section 8 (Session Index):

```markdown
| YYYY-MM-DD | `slug` | Research question in one sentence | One-sentence key finding |
```

### 5 — Confirm synthesis is self-contained

A reader with no prior context should be able to:
- Identify the interesting parameter regime (Section 1–3)
- Know what has already been tested and what hasn't (Section 4–5)
- Trust the empirical numbers (Section 6)
- Run their own next experiment using the guidance (Section 7)

If any of these fail, fix the gap before finishing.

## Scaling guidelines

As the session count grows, synthesis.md will need periodic restructuring:

- **≤ 5 sessions:** flat sections are fine
- **5–15 sessions:** group open questions by theme (Enforcement, Market Design, Agent Dynamics, Racing)
- **15+ sessions:** consider promoting synthesis.md to a folder (`synthesis/`) with one
  file per topic area and an index — similar to how KIs are structured in the knowledge base

## Notes

- `synthesis.md` stays in `agent_workspace/` (gitignored) until the research is
  ready to publish — at that point, promote the relevant findings to `docs/` or the
  paper directly.
- When in doubt, less is more. A tight synthesis of 3 solid findings is more useful
  than a 10-page dump of every experiment that ran.
