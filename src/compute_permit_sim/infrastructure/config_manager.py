"""Scenario Management Module.

Handles listing, loading, and saving of scenario configurations.
Enforces the strictly typed ScenarioConfig schema.
"""

import json
from pathlib import Path
from typing import List

from ..schemas import ScenarioConfig

SCENARIO_DIR = Path.cwd() / "scenarios"


def list_scenarios() -> List[str]:
    """List all available scenario files in the scenarios directory.

    Returns:
        List of filenames (e.g., ['baseline.json', 'high_risk.json']).
    """
    if not SCENARIO_DIR.exists():
        return []
    return [f.name for f in SCENARIO_DIR.glob("*.json")]


def load_scenario(filename: str) -> ScenarioConfig:
    """Load and validate a scenario from a JSON file.

    Args:
        filename: Name of the file (e.g. 'baseline.json').

    Returns:
        Validated ScenarioConfig object.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValidationError: If JSON doesn't match schema.
    """
    file_path = SCENARIO_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # validate via Pydantic
    return ScenarioConfig(**data)


def save_scenario(config: ScenarioConfig, filename: str) -> None:
    """Save a scenario configuration to a JSON file.

    Args:
        config: The ScenarioConfig object to save.
        filename: Target filename.
    """
    SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    file_path = SCENARIO_DIR / filename

    # model_dump_json() is Pydantic v2, simpler than json.dump(model.dict())
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(config.model_dump_json(indent=2))
