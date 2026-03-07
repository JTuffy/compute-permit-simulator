"""Scenario Management Module.

Handles listing, loading, and saving of scenario configurations and sweep definitions.
Enforces the strictly typed ScenarioConfig schema.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..schemas import ScenarioConfig

SCENARIO_DIR = Path.cwd() / "scenarios"
BASIC_DIR = SCENARIO_DIR / "basic"  # canonical scenario JSONs
SWEEP_DIR = SCENARIO_DIR / "sweeps"  # sweep definition JSONs


def list_scenarios() -> list[str]:
    """List all available scenario files.

    Returns:
        Sorted list of paths relative to ``SCENARIO_DIR``
        (e.g. ``['basic/scenario_1_minimal.json']``).
    """
    if not BASIC_DIR.exists():
        return []
    return sorted(f"basic/{f.name}" for f in BASIC_DIR.glob("*.json"))


def list_scenario_names() -> list[tuple[str, str]]:
    """Return (display_name, filename) pairs for all available scenarios.

    Loads each scenario file to extract its human-readable ``name``.  If loading
    fails the raw filename is used as the display name.

    Returns:
        Sorted-by-display-name list of ``(name, relative_filename)`` tuples.
    """
    pairs: list[tuple[str, str]] = []
    for filename in list_scenarios():
        try:
            cfg = load_scenario(filename)
            pairs.append((cfg.name or filename, filename))
        except Exception:  # noqa: BLE001
            pairs.append((filename, filename))
    return sorted(pairs, key=lambda t: t[0])


# ---------------------------------------------------------------------------
# Sweep config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SweepConfig:
    """Definition of a 1D parameter sweep loaded from a JSON file."""

    scenario_file: (
        str  # path relative to scenarios/, e.g. "basic/scenario_1_minimal.json"
    )
    param_path: str  # dot-path, e.g. "audit.base_prob"
    param_label: str  # human-readable label for charts/exports
    min_val: float  # sweep start (inclusive)
    max_val: float  # sweep end (inclusive)
    interval: float  # step between values
    n_runs: int = 50  # Monte Carlo replications per point
    seeds: list[int] = field(default_factory=list)  # empty = use 0..n_runs-1


def list_sweeps() -> list[str]:
    """List all available sweep definition files.

    Returns:
        List of filenames relative to scenarios/sweeps/.
    """
    if not SWEEP_DIR.exists():
        return []
    return sorted([f.name for f in SWEEP_DIR.glob("*.json")])


def load_sweep(filename: str) -> SweepConfig:
    """Load and validate a sweep definition from a JSON file.

    The JSON format is::

        {
            "scenario_file": "basic/scenario_1_minimal.json",
            "param_path": "audit.base_prob",
            "param_label": "Base Audit Rate π₀",
            "min_val": 0.01,
            "max_val": 0.30,
            "interval": 0.05,
            "n_runs": 50
        }

    Args:
        filename: Name of the sweep file (e.g. 'sweep_pi0_lawless.json').

    Returns:
        Validated SweepConfig dataclass.

    Raises:
        FileNotFoundError: If file doesn't exist.
        KeyError / ValueError: If JSON is malformed or range is invalid.
    """
    file_path = SWEEP_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Sweep file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    min_val = float(data["min_val"])
    max_val = float(data["max_val"])
    interval = float(data["interval"])

    if interval <= 0:
        raise ValueError(f"interval must be > 0, got {interval}")
    if min_val > max_val:
        raise ValueError(f"min_val ({min_val}) must be <= max_val ({max_val})")

    return SweepConfig(
        scenario_file=data["scenario_file"],
        param_path=data["param_path"],
        param_label=data.get("param_label", data["param_path"]),
        min_val=min_val,
        max_val=max_val,
        interval=interval,
        n_runs=int(data.get("n_runs", 50)),
        seeds=[int(s) for s in data.get("seeds", [])],
    )


def load_scenario(filename: str) -> ScenarioConfig:
    """Load and validate a scenario from a JSON file.

    Args:
        filename: Path relative to ``SCENARIO_DIR``, e.g.
                  ``'basic/scenario_1_minimal.json'``.

    Returns:
        Validated ScenarioConfig object.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValidationError: If JSON doesn't match schema.
    """
    file_path = SCENARIO_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    return ScenarioConfig(**data)


def save_scenario(config: ScenarioConfig, filename: str) -> None:
    """Save a scenario configuration to a JSON file.

    Args:
        config: The ScenarioConfig object to save.
        filename: Path relative to ``SCENARIO_DIR``, e.g.
                  ``'basic/my_scenario.json'``.
    """
    file_path = SCENARIO_DIR / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(config.model_dump_json(indent=2))
