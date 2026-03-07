"""Tests for config_manager: list_scenarios, load_scenario, save_scenario."""

import json
from pathlib import Path
from unittest.mock import patch

import compute_permit_sim.services.config_manager as config_manager_module

_EXAMPLE_SCENARIO = {
    "name": "Validation Test",
    "steps": 10,
    "n_agents": 5,
    "market": {"permit_cap": 100},
    "audit": {"base_prob": 0.05, "penalty_amount": 10},
    "lab": {},
}


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


class TestListScenarios:
    def test_returns_basic_prefixed_paths(self, tmp_path: Path) -> None:
        basic = tmp_path / "basic"
        basic.mkdir()
        _write(basic / "s1.json", _EXAMPLE_SCENARIO)
        _write(basic / "s2.json", _EXAMPLE_SCENARIO)
        with (
            patch.object(config_manager_module, "SCENARIO_DIR", tmp_path),
            patch.object(config_manager_module, "BASIC_DIR", basic),
        ):
            result = config_manager_module.list_scenarios()
        assert result == ["basic/s1.json", "basic/s2.json"]

    def test_empty_when_basic_dir_missing(self, tmp_path: Path) -> None:
        with (
            patch.object(config_manager_module, "SCENARIO_DIR", tmp_path),
            patch.object(config_manager_module, "BASIC_DIR", tmp_path / "basic"),
        ):
            result = config_manager_module.list_scenarios()
        assert result == []

    def test_sorted_alphabetically(self, tmp_path: Path) -> None:
        basic = tmp_path / "basic"
        basic.mkdir()
        for name in ["gamma.json", "alpha.json", "beta.json"]:
            _write(basic / name, _EXAMPLE_SCENARIO)
        with (
            patch.object(config_manager_module, "SCENARIO_DIR", tmp_path),
            patch.object(config_manager_module, "BASIC_DIR", basic),
        ):
            result = config_manager_module.list_scenarios()
        assert result == ["basic/alpha.json", "basic/beta.json", "basic/gamma.json"]


class TestLoadScenario:
    def test_loads_from_basic_subpath(self, tmp_path: Path) -> None:
        basic = tmp_path / "basic"
        basic.mkdir()
        _write(basic / "test.json", _EXAMPLE_SCENARIO)
        with patch.object(config_manager_module, "SCENARIO_DIR", tmp_path):
            config = config_manager_module.load_scenario("basic/test.json")
        assert config.name == "Validation Test"
        assert config.audit.base_prob == 0.05

    def test_not_found_raises(self, tmp_path: Path) -> None:
        with patch.object(config_manager_module, "SCENARIO_DIR", tmp_path):
            try:
                config_manager_module.load_scenario("basic/nonexistent.json")
                assert False, "Should have raised"
            except FileNotFoundError:
                pass


class TestSaveScenario:
    def test_save_creates_file_in_subdirectory(self, tmp_path: Path) -> None:
        basic = tmp_path / "basic"
        basic.mkdir()
        _write(basic / "original.json", _EXAMPLE_SCENARIO)
        with patch.object(config_manager_module, "SCENARIO_DIR", tmp_path):
            config = config_manager_module.load_scenario("basic/original.json")
            config_manager_module.save_scenario(config, "basic/saved.json")
        assert (basic / "saved.json").exists()

    def test_save_creates_parent_dir_if_missing(self, tmp_path: Path) -> None:
        basic = tmp_path / "basic"
        basic.mkdir()
        _write(basic / "original.json", _EXAMPLE_SCENARIO)
        with patch.object(config_manager_module, "SCENARIO_DIR", tmp_path):
            config = config_manager_module.load_scenario("basic/original.json")
            config_manager_module.save_scenario(config, "new_subdir/saved.json")
        assert (tmp_path / "new_subdir" / "saved.json").exists()
