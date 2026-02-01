"""Verify scenario manager functionality."""

from compute_permit_sim.infrastructure.config_manager import (
    SCENARIO_DIR,
    list_scenarios,
    load_scenario,
    save_scenario,
)


def test_manager():
    print("Listing scenarios...")
    scenarios = list_scenarios()
    print(f"Found: {scenarios}")
    assert "baseline.json" in scenarios
    assert "high_risk.json" in scenarios
    assert "strict_audit.json" in scenarios

    print("Loading baseline...")
    config = load_scenario("baseline.json")
    print(f"Loaded: {config.name}")
    assert config.audit.base_prob == 0.05

    print("Saving test scenario...")
    config_copy = config.model_copy()
    # Pydantic v2 copy/update might differ, let's just save as is for now or assume immutability
    # standard pydantic doesn't let you easily mutate frozen=.
    # We will just save the loaded one as test_save.json
    save_scenario(config, "test_save.json")

    assert (SCENARIO_DIR / "test_save.json").exists()
    print("Verification passed!")

    # Cleanup
    (SCENARIO_DIR / "test_save.json").unlink()


if __name__ == "__main__":
    test_manager()
