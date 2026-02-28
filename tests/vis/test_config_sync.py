"""Sync guard tests — detect config parameter drift.

These tests ensure that every field in ScenarioConfig (and its sub-models)
is wired through UIConfig, UrlConfig, and the Excel export.

If you add a field to AuditConfig/LabConfig/MarketConfig/ScenarioConfig,
these tests will fail until you add it to all downstream surfaces.
"""

from compute_permit_sim.schemas.config import (
    AuditConfig,
    LabConfig,
    MarketConfig,
    ScenarioConfig,
)
from compute_permit_sim.vis.state.config import UIConfig

# ── Helpers ──────────────────────────────────────────────────────────────────

# Fields that are intentionally excluded from UIConfig sync
# (e.g. metadata-only fields that aren't user-facing)
_UICONFIG_SKIP = {"name", "description", "audit", "market", "lab"}


def _flatten_fields(model_class, prefix=""):
    """Yield (dotpath, field_info) for all leaf fields, recursing into sub-models."""
    sub_models = {AuditConfig, LabConfig, MarketConfig}
    for name, info in model_class.model_fields.items():
        dotpath = f"{prefix}{name}" if prefix else name
        if info.annotation in sub_models:
            yield from _flatten_fields(info.annotation, f"{dotpath}.")
        else:
            yield dotpath, info


# ── Tests ────────────────────────────────────────────────────────────────────


def test_uiconfig_has_all_scenario_fields():
    """Every leaf field in ScenarioConfig must have a reactive in UIConfig."""
    ui = UIConfig()
    missing = []

    for dotpath, _ in _flatten_fields(ScenarioConfig):
        if dotpath in _UICONFIG_SKIP:
            continue

        # UIConfig uses short names (no dots), map dotpaths → attribute names
        # e.g. "audit.base_prob" → "base_prob", "lab.economic_value_min" → "economic_value_min"
        # Top-level fields keep their name ("n_agents" → "n_agents")
        attr_name = dotpath.split(".")[-1]

        # Special name mappings in UIConfig
        # Most fields match 1:1 with the domain model leaf name.
        name_map: dict[str, str] = {}
        attr_name = name_map.get(attr_name, attr_name)

        if not hasattr(ui, attr_name):
            missing.append(f"{dotpath} → expected UIConfig.{attr_name}")

    assert not missing, (
        f"UIConfig is missing reactive fields for {len(missing)} ScenarioConfig fields:\n"
        + "\n".join(f"  • {m}" for m in missing)
    )


def test_to_from_scenario_config_roundtrip():
    """UIConfig.to_scenario_config() → from_scenario_config() round-trips."""
    ui = UIConfig()

    # Set distinctive values
    # UIConfig attributes are created dynamically via setattr in __init__;
    # mypy can't resolve them statically, so we suppress attr-defined here.
    ui.n_agents.value = 42  # type: ignore[attr-defined]
    ui.steps.value = 77  # type: ignore[attr-defined]
    ui.penalty_amount.value = 999.0  # type: ignore[attr-defined]
    ui.flop_threshold.value = 1e23  # type: ignore[attr-defined]
    ui.collateral_amount.value = 50.0  # type: ignore[attr-defined]
    ui.whistleblower_prob.value = 0.15  # type: ignore[attr-defined]
    ui.racing_gap_sensitivity.value = 0.5  # type: ignore[attr-defined]
    ui.capability_scale.value = 500.0  # type: ignore[attr-defined]

    config = ui.to_scenario_config()

    # Restore into a fresh UIConfig
    ui2 = UIConfig()
    ui2.from_scenario_config(config)

    config2 = ui2.to_scenario_config()

    # Compare all fields
    assert config.model_dump() == config2.model_dump(), (
        "Round-trip mismatch between to_scenario_config() -> from_scenario_config()"
    )


def test_scenario_config_fields_have_ui_metadata():
    """Every leaf field in sub-models should have json_schema_extra with ui_group/ui_label."""
    missing = []
    for dotpath, info in _flatten_fields(ScenarioConfig):
        if dotpath in _UICONFIG_SKIP or dotpath in ("seed",):
            continue
        extra = info.json_schema_extra
        if not extra or "ui_group" not in extra or "ui_label" not in extra:
            missing.append(dotpath)

    assert not missing, (
        f"{len(missing)} fields missing ui metadata (json_schema_extra):\n"
        + "\n".join(f"  • {m}" for m in missing)
    )
