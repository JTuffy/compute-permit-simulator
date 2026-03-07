---
trigger: always_on
description: Meta-rule governing the rule system itself. Read first. Never modify this file — add amendments.md instead.
---

# rules/main.md

<!-- This file is frozen. Do not edit it. Add top-level amendments to amendments.md. -->

## What This Is

Entry point for the rule system. Describes how rules are organized and maintained.
Project conventions belong in sibling files, not here.

## Session Start

1. Read relevant files in `.agents/rules/`
2. Check `.agents/workflows/` — follow an existing workflow before improvising
3. Verify current repo state before assuming it is clean

## Rule File Hierarchy

| File | Update frequency | Purpose |
|---|---|---|
| `main.md` | **Never** — add `amendments.md` | Meta-strategy for the rule system |
| `amendments.md` | Rarely — high-level only | Top-level notes that don't fit elsewhere |
| `coding.md` / `python.md` | Rarely — durable patterns only | Language and coding conventions |
| `project.md` | When project patterns change | Project-specific decisions and conventions |

## What Belongs Where

- **`amendments.md`**: top-level notes that apply across the entire project and don't fit a more specific file. Keep sparse.
- **`coding.md`**: general principles applicable to any codebase (layering, change discipline, reasoning in comments). Update only when a proven cross-project pattern is newly captured.
- **`python.md`**: Python-specific conventions (tooling, type safety, testing patterns). Update only for durable, project-agnostic improvements.
- **`project.md`**: decisions and patterns specific to this codebase. Update when a new architectural decision is made, a consistent pattern emerges, or a known pitfall should be documented. Entries should be understandable without deep context — written for an agent implementing a similar feature from scratch.

## What project.md Should Look Like

Project.md captures *why* and *how* things are structured, not low-level implementation details. An entry should answer: "what do I need to know to implement something consistent with how we've done it before?" Avoid hardcoding specific values, icons, or file paths unless they are canonical reference points. Prefer short prose describing intent over exhaustive lists of specifics.

## Definition of Done

- Automated checks pass
- Ask: new durable pattern? → update the appropriate rule file
- Ask: repeated manual procedure? → add or update a workflow file