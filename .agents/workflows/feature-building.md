---
description: How to build a new feature — meta checklist for consistency, state design, and cross-feature review.
---

# Feature Building Workflow

Use before implementing any non-trivial feature.

## Before writing code

1. **Find existing analogues.** What features already do something similar? List them. Your feature must follow the same pattern — not invent a new one. Review the projects.md rules file for existing patterns. Review what is alreayd supported, and what intentional designs exist and choices, so we can decide if and what to extend. Keep this up to date as a living document.

2. Design in interfaces and features. Consider not just the code you need, but what interfaces, services, etc are required, how you can design those solidly first, then design those and only after implement them with the specific ode feature you need. Spend a lot of time review the existing code structure and elements before deciding where and how to implement.

3. **Centralize first.** If the new feature shares behaviour with an existing one, extract the shared piece before building on top of it. Never implement the same concern twice with plans to unify later.

IMPORTANT: come back with clarifiyng questions if you can't establiish a best practice or hthink theoverall goal is unclear. 

## During implementation

- Design models and interfaces
- Write tests to moel expected behavior. keep these generic. see test rules. 
- Implement logic
- Once tests pass, review the changeset and what could be improved or what oyu might hve done differently, what could be more professoinal, what is now dead. Consider small rewrites or other generifications to enhance extendability.
- All quality gates pass

## After implementation

- Review new interfaces, patterns, or design decisions you implemented. make sure they are adequatyle reflected in coding.md and project.md (especially) rules. Make sure the project md is an up to date living document. reflect on constitution.md for how to update these, but after finishing a feature ensure project.md is up to date with our core decisiosn (make small, targeted notes and updates) to keep it a living document wihtout ading too much garbgae there. if it starts getting stale, rewrite it.