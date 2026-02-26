import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module to patch, not just the function
import compute_permit_sim.services.config_manager as config_manager_module


@pytest.fixture
def mock_scenario_dir():
    """Create a temporary directory for scenarios."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create a sample scenario file
        scenario_data = {
            "name": "Validation Test",
            "steps": 10,
            "n_agents": 5,
            "market": {"permit_cap": 100},
            "audit": {"base_prob": 0.05, "penalty_amount": 10},
            "lab": {},
        }

        with open(tmp_path / "EXAMPLE_baseline.json", "w") as f:
            json.dump(scenario_data, f)

        with open(tmp_path / "EXAMPLE_high_risk.json", "w") as f:
            json.dump(scenario_data, f)

        with open(tmp_path / "EXAMPLE_strict_audit.json", "w") as f:
            json.dump(scenario_data, f)

        # Patch the SCENARIO_DIR in the module
        with patch.object(config_manager_module, "SCENARIO_DIR", tmp_path):
            yield tmp_path


def test_manager(mock_scenario_dir):
    print("Listing scenarios...")
    scenarios = config_manager_module.list_scenarios()
    print(f"Found: {scenarios}")
    assert "EXAMPLE_baseline.json" in scenarios
    assert "EXAMPLE_high_risk.json" in scenarios
    assert "EXAMPLE_strict_audit.json" in scenarios

    print("Loading baseline...")
    config = config_manager_module.load_scenario("EXAMPLE_baseline.json")
    print(f"Loaded: {config.name}")
    assert config.audit.base_prob == 0.05

    print("Saving test scenario...")
    config_manager_module.save_scenario(config, "test_save.json")

    assert (mock_scenario_dir / "test_save.json").exists()
    print("Verification passed!")
