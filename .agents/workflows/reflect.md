---
description: Self-improvement of agent rules and workflows — reflects on past work, code history, and process quality to make targeted, high-value updates.
---

# Reflect Workflow

Use this workflow deliberately and infrequently — when you sense the rules have drifted,
when a session felt unnecessarily laborious, or when the user asks for a rules review.
This is not a code task; it is a meta-task about the quality of the agent's own process.

## Intent

Reflect does not look for bugs in code. It asks: **could the agent have worked smarter?**
It surfaces friction, redundancy, or philosophical misalignment in the rules, and makes
small, targeted improvements. Avoid large rewrites — the worst outcome is destabilizing
working rules to chase theoretical purity.

## Before reflecting

1. **Read all rules files** in `.agents/rules/` top-down. Note anything that feels stale,
   contradictory, or so vague it would not actually guide a decision.

2. **Review recent git history** (`git log --oneline -20`). Understand the overall
   direction of work: what features were added, what was refactored, what was removed.
   Look for patterns of repeated rework — these are signals the rules weren't guiding well.

3. **Read recent conversation summaries** if acessible. Identify sessions where:
   - The agent invented a new approach instead of following an existing pattern
   - Multiple passes were needed to get something right
   - A refactor was done reactively rather than proactively before implementation

## Reflecting

4. For each issue found, ask three questions:
   - Would a clear rule have prevented this?
   - Is a rule already trying to cover this but failing (too vague, too buried)?
   - Is this genuinely a one-off, or a signal of a systemic pattern?

5. **Make changes only if they pass the "useful in the next feature" test.** A rule is
   worth adding if a future agent implementing a random new feature would benefit from it.
   Philosophical musings with no actionable consequence should be omitted.

6. Keep changes **small and targeted**:
   - Additions: one or two sentences that capture a decision or constraint clearly
   - Removals: anything that is now dead (patterns that no longer exist in the codebase)
   - Reorders: move the most important items to the top of each section
   - Never rewrite a working rule file wholesale — patch surgically

7. Consider workflow gaps: are there workflows missing that would have prevented repeated
   manual steps? Would a new workflow (`prune-repo`, `reflect`, etc.) have helped?

## After reflecting

8. Summarise what you changed and **why** — write this as a single comment in
   `amendments.md` if the finding is cross-cutting, or update the relevant rule file
   header comment if it's localised.

9. Do NOT add the findings themselves to amendments.md — that file is for top-level notes
   only. The actual improvements go directly into the rule files.
