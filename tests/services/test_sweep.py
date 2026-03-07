"""Tests for the parameter sweep service."""

from __future__ import annotations

from compute_permit_sim.schemas.config import ScenarioConfig
from compute_permit_sim.services.sweep import override_config, run_sweep


class TestOverrideConfig:
    def _base(self) -> ScenarioConfig:
        return ScenarioConfig(n_agents=2, steps=2)

    def test_top_level_override(self) -> None:
        cfg = self._base()
        updated = override_config(cfg, "collateral_amount", 99.0)
        assert updated.collateral_amount == 99.0
        assert cfg.collateral_amount == 0.0  # original unchanged

    def test_nested_override(self) -> None:
        cfg = self._base()
        updated = override_config(cfg, "audit.base_prob", 0.42)
        assert abs(updated.audit.base_prob - 0.42) < 1e-10
        assert cfg.audit.base_prob != 0.42

    def test_deep_nested_override(self) -> None:
        cfg = self._base()
        updated = override_config(cfg, "market.fixed_price", 5.0)
        assert updated.market.fixed_price == 5.0

    def test_original_unmodified(self) -> None:
        cfg = self._base()
        _ = override_config(cfg, "audit.base_prob", 0.99)
        assert cfg.audit.base_prob != 0.99


class TestRunSweep:
    def _base(self) -> ScenarioConfig:
        return ScenarioConfig(n_agents=4, steps=3)

    def test_sweep_length(self) -> None:
        cfg = self._base()
        values = [0.05, 0.10, 0.15]
        result = run_sweep(cfg, "audit.base_prob", values, n_runs=2)
        assert len(result.points) == len(values)

    def test_sweep_param_values_preserved(self) -> None:
        cfg = self._base()
        values = [0.1, 0.2, 0.3]
        result = run_sweep(cfg, "audit.base_prob", values, n_runs=2)
        for point, v in zip(result.points, values):
            assert abs(point.param_value - v) < 1e-10

    def test_sweep_metadata(self) -> None:
        cfg = ScenarioConfig(name="MySim", n_agents=2, steps=2)
        result = run_sweep(
            cfg, "collateral_amount", [0.0, 10.0], param_label="Collateral K", n_runs=2
        )
        assert result.scenario_name == "MySim"
        assert result.param_path == "collateral_amount"
        assert result.param_label == "Collateral K"

    def test_compliance_series_shape(self) -> None:
        cfg = self._base()
        values = [0.05, 0.20]
        result = run_sweep(cfg, "audit.base_prob", values, n_runs=3)
        series = result.compliance_series()
        assert len(series) == 2
        for param_val, mean, std in series:
            assert 0.0 <= mean <= 1.0
            assert std >= 0.0

    def test_same_seeds_across_points(self) -> None:
        """Using fixed seeds means param variation, not noise, drives differences."""
        cfg = self._base()
        r1 = run_sweep(cfg, "audit.base_prob", [0.05], seeds=[7, 8, 9])
        r2 = run_sweep(cfg, "audit.base_prob", [0.05], seeds=[7, 8, 9])
        assert (
            abs(
                r1.points[0].result.avg_compliance.mean
                - r2.points[0].result.avg_compliance.mean
            )
            < 1e-10
        )

    def test_default_param_label(self) -> None:
        cfg = self._base()
        result = run_sweep(cfg, "audit.base_prob", [0.1], n_runs=2)
        assert result.param_label == "audit.base_prob"
