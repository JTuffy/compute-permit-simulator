## Summary

Fixes from code review of #11: seeded RNG bug, misleading metric names, and scenario cleanup.

## What changed

- **RNG fix**: fixed-price market tie-breaking now uses the sim's seeded RNG instead of the global one, so results are reproducible
- **Metric renames**: `false_positive_rate` → `compliant_audit_fraction` (no longer clashes with the config param), `detection_rate` → `detection_rate_given_audit` (clarifies it's conditional on audit). Updated everywhere — schemas, MC service, CSV/Excel export, dashboard UI.
- **Scenario consolidation**: merged scenario 4 (dynamic) and 5 (reputation ratchet) into a single **Scenario 4 — Feedback-Driven Compliance** with weaker parameters (base_prob=0.20, penalty=$50M) that still converges to ~97% compliance. Renamed scenario 6 → 5 (enforcement cycles). Removed lawless scenario (degenerate, already covered by scenario 1).
- **Name cleanup**: replaced all remaining "lawless/crisis/maxwell" references with "minimal/strict/smart" across Makefile, main.py, defaults, config_manager, sweep files
- **Docstring fixes**: corrected `p_catch` formula in AuditConfig, "six-phase" → "seven-phase" in game loop

## Test plan

- [x] 132 tests pass
- [ ] Run `make mc` and check CSV column headers
- [ ] Run scenarios 4 and 5 in dashboard, verify ratchet vs oscillation behaviour
