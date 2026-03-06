"""Schema round-trip tests.

Verifies that ScenarioConfig and sub-models can be serialised and deserialised
without data loss, and that default values are internally consistent.
"""

import pytest

from compute_permit_sim.schemas.config import (
    AuditConfig,
    LabConfig,
    MarketConfig,
    ScenarioConfig,
)


def _roundtrip(model_cls, instance):
    """Serialise to dict and reconstruct — should be identical."""
    data = instance.model_dump()
    reconstructed = model_cls(**data)
    assert reconstructed == instance, (
        f"{model_cls.__name__} round-trip failed:\n"
        f"  original:      {instance}\n"
        f"  reconstructed: {reconstructed}"
    )
    return reconstructed


class TestSchemaRoundTrip:
    """Ensures every sub-model survives a model_dump / reconstruct cycle."""

    def test_audit_config_defaults(self):
        _roundtrip(AuditConfig, AuditConfig())

    def test_market_config_defaults(self):
        _roundtrip(MarketConfig, MarketConfig())

    def test_lab_config_defaults(self):
        _roundtrip(LabConfig, LabConfig())

    def test_scenario_config_defaults(self):
        _roundtrip(ScenarioConfig, ScenarioConfig())

    def test_scenario_config_json_roundtrip(self):
        """JSON serialise → parse → reconstruct."""
        original = ScenarioConfig()
        json_str = original.model_dump_json()
        reconstructed = ScenarioConfig.model_validate_json(json_str)
        assert reconstructed == original

    def test_scenario_config_exclude_defaults_roundtrip(self):
        """exclude_defaults=True (used for URL encoding) must still round-trip."""
        original = ScenarioConfig()
        sparse = original.model_dump(exclude_defaults=True, exclude_none=True)
        # Reconstruct — missing fields should materialise from schema defaults
        reconstructed = ScenarioConfig(**sparse)
        assert reconstructed == original, (
            "exclude_defaults round-trip diverged — a default value changed "
            "without updating the schema default. sparse dict was:\n"
            f"{sparse}"
        )

    @pytest.mark.parametrize(
        "field,value",
        [
            ("n_agents", 50),
            ("steps", 200),
            ("collateral_amount", 250.0),
            ("flop_threshold", 1e26),
        ],
    )
    def test_scenario_config_non_default_roundtrip(self, field: str, value):
        """Non-default values must survive round-trip too."""
        instance = ScenarioConfig(**{field: value})
        _roundtrip(ScenarioConfig, instance)
        assert getattr(instance, field) == value
