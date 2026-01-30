# Coding Standards & Best Practices

This document outlines the coding standards for the `aisc-cm-simulator` project. We adhere to **strict** Python quality standards to ensure maintainability, readability, and correctness.

## 1. General Philosophy
-   **Explicit is better than implicit.**
-   **Readability counts.**
-   **Type hints are mandatory.**
-   **Documentation is mandatory.**

## 2. Tooling
We use `ruff` for both linting and formatting.
-   **Linter**: `ruff check` with strict rules enabled (see `pyproject.toml`).
-   **Formatter**: `ruff format` (compatible with Black).

## 3. Style Guidelines

### 3.1 Naming Conventions
-   **Variables/Functions/Methods**: `snake_case`
-   **Classes/Exceptions**: `PascalCase`
-   **Constants**: `UPPER_CASE`
-   **Private Members**: Prefix with `_` (e.g., `_internal_helper`). Only use double `__` for name mangling if absolutely necessary.
-   **Loop Variables**: Use descriptive names. Avoid single-letter variables like `i`, `x` unless in very short, idiomatic loops (e.g. strict comprehensions). For `range()` loops over simulation steps, use `step` or `tick`.

### 3.2 Type Hinting
-   All function signatures must have type hints.
-   Use built-in types (`list`, `dict`, `tuple`) for Python 3.9+.
-   Use `typing.Optional`, `typing.Union`, `typing.Any` (sparingly) where appropriate.
-   Return types must be specified, including `-> None`.

### 3.3 Docstrings
-   We follow the **Google Style** for docstrings.
-   Every module, class, and public method must have a docstring.
-   **Structure**:
    ```python
    def function(arg1: int) -> bool:
        """Short summary of what the function does.

        Longer detailed explanation if necessary.

        Args:
            arg1: Description of arg1.

        Returns:
            Description of return value.
        """
        ...
    ```

### 3.4 Formatting
-   Line length: **120 characters**.
-   Indent: **4 spaces**.
-   Imports: Sorted and grouped automatically by `ruff` (isort rules).

## 4. Code Structure
-   Group related logic into classes or modules.
-   Avoid global variables.
-   Use `if __name__ == "__main__":` for script execution blocks.

## 5. Development Workflow
1.  Make changes.
2.  Run `ruff check . --fix`.
3.  Run `ruff format .`.
4.  Run tests (if available).
