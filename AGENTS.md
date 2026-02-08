# Developer Guidelines & Agent Rules

This document outlines the architectural patterns, best practices, and rules for developing the Compute Permit Simulator. All AI agents and developers must adhere to these guidelines to ensure maintainability, performance, and stability.

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
  - **Debounce Effects**: Heavy side-effects (like URL updates or I/O) triggered by reactive variables must be debounced using `solara.lab.use_task` and `asyncio.sleep()`.
  - **Batch Updates**: When updating multiple reactive variables (e.g., loading a scenario), be aware of cascade effects.

### Testing
- **Factories**: Use `tests/factories.py` for creating test data. Do not instantiate complex Pydantic models manually in tests.
- **Isolation**: Tests touching the filesystem (e.g., `config_manager`) must use `tempfile` and `unittest.mock` to avoid polluting the workspace or locking files.

## 3. Workflow Rules

1. **Modify Schemas First**: When adding a parameter, add it to `schemas/config.py` first.
2. **Update UI State**: Then update `vis/state/config.py` to expose it reactively.
3. **Update Logic**: Then implement the logic in `services/`.
4. **Verify**: Run `pytest` to ensure no regressions.

## 4. Common Pitfalls to Avoid

- **Duplicate definitions**: Do not create `UIAuditConfig` if `AuditConfig` exists. Use the existing schema.
- **Synchronous blocking**: Do not run heavy computation in `solara.use_effect` without `use_task`.
- **Stale Imports**: When moving classes, grep the entire codebase for old import paths.