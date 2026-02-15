# Developer Guidelines & Agent Rules

Guidelines for the Compute Permit Simulator. For detailed architecture diagrams, see `documents/TECHNICAL_DOCUMENTATION.md`.

## Commands

```bash
pytest                           # Verify all tests pass
pytest tests/test_file.py -v     # Single file test
solara run vis/app.py            # Start UI
mypy .                           # Run type checker
```

## 1. Architecture Overview

### Core Domains
- **`schemas/`**: Single source of truth for all data models. Pydantic is used strictly.
  - `config.py`: Configuration schemas (`ScenarioConfig`, `AuditConfig`). **Immutable/Frozen** by default.
  - `data.py`: Runtime data (`SimulationRun`, `StepResult`).
- **`services/`**: Business logic and orchestration.
  - `simulation.py`: The `SimulationEngine` class.
  - `engine_instance.py`: The singleton `engine` instance (separate to avoid circular imports).
  - `config_manager.py`: File I/O for scenarios.
- **`vis/`**: UI layer (Solara).
  - `state/`: Reactive state containers (e.g., `UIConfig`). **Must map directly to Schemas.**
  - `components/`: Reusable UI widgets.
  - `plotting/`: Pure plotting logic (matplotlib/pandas), no Solara dependencies.

## 2. Coding Standards

### Dependency Management
- **No Circular Imports**:
  - `vis` modules import `services`.
  - `services` modules **NEVER** import `vis` (except for dependency injection in `engine_instance.py`).
  - Use `typing.TYPE_CHECKING` for type hint imports that would otherwise cause cycles.
  - Export singletons from dedicated files (e.g., `engine_instance.py`) if they bind disjoint layers.

### Configuration & State
- **DRY Models**: Do not duplicate Pydantic models for UI state.
  - Use `ScenarioConfig` as the canonical definition.
  - `vis.state.config.UIConfig` should map reactive fields *directly* to/from `ScenarioConfig`.
- **Performance**:
  - **Debounce Effects**: Heavy side-effects triggered by reactive variables must be debounced:
    ```python
    # Wrong - fires every keystroke
    solara.use_effect(lambda: save_to_disk(), [value])

    # Correct - debounced
    async def debounced_save():
        await asyncio.sleep(0.3)
        save_to_disk()
    solara.lab.use_task(debounced_save, dependencies=[value])
    ```
  - **Batch Updates**: When updating multiple reactive variables (e.g., loading a scenario), be aware of cascade effects.

### Testing
- **Factories**: Use `tests/factories.py` for creating test data. Do not instantiate complex Pydantic models manually in tests.
- **Isolation**: Tests touching the filesystem (e.g., `config_manager`) must use `tempfile` and `unittest.mock` to avoid polluting the workspace or locking files.

## 3. Workflow Rules

1. **Modify Schemas First**: When adding a parameter, add it to `schemas/config.py` first.
2. **Update UI State**: Then update `vis/state/config.py` to expose it reactively.
3. **Update Logic**: Then implement the logic in `services/`.
4. **Verify**: Run `pytest` and `mypy .` to ensure no regressions.

## 4. Boundaries

### ✅ Always
- Modify `schemas/config.py` first when adding parameters
- Use factories from `tests/factories.py` for test data
- Use `solara.lab.use_task` with `asyncio.sleep()` for heavy side-effects
- Run `pytest` after changes

### ⚠️ Ask First
- Adding new dependencies
- Modifying config file formats
- Deleting files or removing functionality
- Changes to `services/engine_instance.py`

### 🚫 Never
- Import `vis` from `services` (circular imports)
- Duplicate Pydantic models (e.g., creating `UIAuditConfig` when `AuditConfig` exists)
- Run heavy computation in `solara.use_effect` without `use_task`
- Commit secrets or credentials

## 5. Refactoring Triggers

Refactor when:
- Schema has >5 optional fields with interdependencies → extract sub-schema
- Component file >200 lines → split into subcomponents
- Same pattern appears 3+ times → extract helper
- Test requires >3 mocks → simplify dependencies