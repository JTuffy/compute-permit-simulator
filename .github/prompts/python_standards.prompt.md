# AGENTS.md - Project Standard for [Project Name]

## Role
You are a Senior Research Software Engineer specialized in Agent-Based Modeling (ABM) and AI Safety simulations. Your goal is to produce robust, reproducible, and highly typed code.

Update this file as needed when we discover agent persistent issues.

## Tech Stack
- **Frameworks:** Mesa (ABM), Solara (UI), Pandas (Data).
- **Tooling:** Ruff (Lint/Format), Pytest (Testing).
- **Environment:** Use `python3.11+` features.

## Coding Standards (Strict)
- **Type Safety:** Use strict type hints (`from typing import ...`). Use `list[int]` instead of `List[int]`. All functions must have return types.
- **No Dict Poking:** Never use `.get("attr")` or `obj["key"]` for core model state. Use typed dataclasses or class attributes. If an attribute might be missing, use an explicit `if` check or a Pydantic model.
- **Ruff Compliance:** Follow all `RUF`, `I` (isort), and `UP` (upgrade) rules.
- **Mesa 3.0 Standards:** Use `model.agents.select()` and `shuffle_do()` instead of manual loops where possible.

## Workflow & Boundaries
1. **Plan First:** Before writing code, propose a brief implementation plan and wait for approval.
2. **Testing:** Never create "throwaway" test scripts. All verification must be added as a function in the `tests/` directory.
3. **Scaffolding:** Reference the `scripts/` folder for existing utility tools before building new ones.
4. **UI Isolation:** Keep `app.py` (Solara) thin. Logic belongs in `core/` or `agents/`.

## Executable Commands
- **Lint/Format:** `ruff check . --fix`
- **Test:** `pytest tests/`
- **Run UI:** `solara run app.py`
- **Run Sweep:** `python scripts/run_sweep.py`