---
trigger: always_on
description: Python-specific conventions — tooling, typing, patterns, and project structure.
---

# rules/python.md

<!-- Applies to all Python work. Nothing in this file is project-specific. -->

## Tooling

Use `uv` for all Python environment and dependency operations
or pipenv directly.

```
uv sync                    # install all dependencies
uv add <pkg>               # add runtime dependency
uv add --dev <pkg>         # add dev dependency
uv run python ...          # always run Python through uv
uv run pytest -q           # run tests
uv run ruff check . --fix  # lint (with auto-fix)
uv run ruff format .       # format
uv run mypy .              # type check
```

Makefile targets may wrap these but are not guaranteed to work in all environments.
When in doubt, use `uv run` directly.

## Type Safety

- All function signatures and class fields MUST be fully typed.
- NEVER use `getattr(obj, "field_as_string")` on typed objects. Use direct attribute access.
- NEVER use bare `assert isinstance(x, T)` in production paths — raise `TypeError` with context.
- Use `TYPE_CHECKING` guards for hint-only imports that would create circular dependencies.
- Pydantic v2 models: prefer `ConfigDict(frozen=True)` unless mutability is explicitly justified.
  Use `model_copy(update={...})` for single-field mutations on frozen models.

## Patterns

**Schema-first.** Define data shapes (Pydantic models, dataclasses) before implementing
logic. Logic depends on schemas; schemas do not depend on logic.

**Frozen models.** Immutable models prevent accidental mutation in concurrent or reactive
contexts. Make mutability opt-in, not opt-out.

**One state update, one re-render.** When multiple fields change together, update them
in a single call rather than sequentially — prevents N intermediate renders or observer
firings. Applies to reactive state management (Solara, RxPY, etc.) and event-driven systems.

**No string-keyed dynamic access.** `obj.__dict__["key"]`, `getattr(obj, var)`, and
`obj["key"]` on typed objects bypass type checking. Use typed attributes.

## Testing Conventions

- Mirror source layout: `tests/module/test_file.py` covers `src/module/file.py`.
- Complex model construction belongs in a `factories.py` module — not inline in tests.
- Filesystem tests: always use `tempfile` and `unittest.mock.patch` for path isolation.
- Sync guard tests: if your codebase mirrors a schema into another layer (e.g. UI state),
  maintain a test that detects when the two drift apart. Fail fast on schema changes.
- Do not chase coverage %. Test logic correctness and schema validation first.

## Refactor Triggers

| Signal | Action |
|---|---|
| Same logic in 3+ places | Extract helper or base class |
| Function has >3 parameters with interdependencies | Extract a config/param object |
| Test requires >3 mocks | Simplify the dependency graph |
| File exceeds ~200 lines of logic | Consider splitting by concern |

## Naming

- Functions: `verb_noun` (e.g. `run_single`, `export_csv`)
- Background thread workers: `_verb_noun_background` (private, daemon pattern)
- Private module helpers: `_name` prefix
- Constants: `UPPER_SNAKE_CASE` — collected in a dedicated `defaults.py` or `constants.py`
- Test files: `test_<module_name>.py` matching the module they cover