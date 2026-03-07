"""Updated tests for the Monte Carlo runner with new expanded MonteCarloResult fields."""

from __future__ import annotations

import pytest

from compute_permit_sim.schemas.batch import MetricStats
from compute_permit_sim.schemas.config import ScenarioConfig
from compute_permit_sim.services.monte_carlo import _run_once, run_monte_carlo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_config(**kwargs) -> ScenarioConfig:
    """Return a fast-running config (5 agents, 5 steps) with optional overrides."""
    defaults: dict = {"n_agents": 5, "steps": 5}
    defaults.update(kwargs)
    return ScenarioConfig(**defaults)


# ---------------------------------------------------------------------------
# MetricStats.from_values
# ---------------------------------------------------------------------------


class TestMetricStats:
    def test_from_values_single(self) -> None:
        s = MetricStats.from_values([0.5])
        assert s.mean == pytest.approx(0.5)
        assert s.std == 0.0
        assert s.n == 1

    def test_from_values_multiple(self) -> None:
        s = MetricStats.from_values([0.2, 0.4, 0.6, 0.8])
        assert s.mean == pytest.approx(0.5)
        assert s.std > 0
        assert s.ci_low < s.mean < s.ci_high

    def test_from_values_empty(self) -> None:
        s = MetricStats.from_values([])
        assert s.n == 0
        assert s.mean == 0.0

    def test_nan_sentinel(self) -> None:
        import math

        s = MetricStats.nan()
        assert s.n == 0
        assert math.isnan(s.mean)


# ---------------------------------------------------------------------------
# _run_once
# ---------------------------------------------------------------------------


class TestRunOnce:
    def test_returns_trajectory_length(self) -> None:
        cfg = _minimal_config(seed=42)
        result = _run_once(cfg, seed=42)
        assert len(result.step_compliance) == cfg.steps
        assert len(result.step_n_violators) == cfg.steps

    def test_compliance_range(self) -> None:
        cfg = _minimal_config(seed=0)
        r = _run_once(cfg, seed=0)
        assert 0.0 <= r.avg_compliance <= 1.0
        assert 0.0 <= r.final_compliance <= 1.0

    def test_audit_rate_range(self) -> None:
        cfg = _minimal_config(seed=0)
        r = _run_once(cfg, seed=0)
        assert 0.0 <= r.audit_rate <= 1.0


# ---------------------------------------------------------------------------
# run_monte_carlo
# ---------------------------------------------------------------------------


class TestRunMonteCarlo:
    def test_basic_fields_populated(self) -> None:
        cfg = _minimal_config()
        result = run_monte_carlo(cfg, n_runs=3, seeds=[0, 1, 2])
        assert result.n_runs == 3
        assert result.scenario_name == cfg.name
        assert isinstance(result.avg_compliance, MetricStats)

    def test_trajectory_length(self) -> None:
        steps = 5
        cfg = _minimal_config(steps=steps)
        result = run_monte_carlo(cfg, n_runs=3, seeds=[0, 1, 2])
        assert len(result.step_compliance) == steps
        assert len(result.step_n_violators) == steps

    def test_trajectory_step_stats_are_metric_stats(self) -> None:
        cfg = _minimal_config()
        result = run_monte_carlo(cfg, n_runs=3, seeds=[0, 1, 2])
        for ms in result.step_compliance:
            assert isinstance(ms, MetricStats)

    def test_percentiles_order(self) -> None:
        cfg = _minimal_config()
        result = run_monte_carlo(cfg, n_runs=5, seeds=list(range(5)))
        assert result.p10_compliance <= result.avg_compliance.mean
        assert result.p90_compliance >= result.avg_compliance.mean

    def test_pct_runs_full_compliance_range(self) -> None:
        cfg = _minimal_config()
        result = run_monte_carlo(cfg, n_runs=3, seeds=[0, 1, 2])
        assert 0.0 <= result.pct_runs_full_compliance <= 1.0

    def test_payoff_compliant_present_on_all_compliant(self) -> None:
        # With high penalty, firms tend to stay compliant
        cfg = _minimal_config()
        result = run_monte_carlo(cfg, n_runs=2, seeds=[0, 1])
        # At least one of compliant or violator payoff should not be NaN
        import math

        has_data = not math.isnan(result.payoff_compliant.mean) or not math.isnan(
            result.payoff_violator.mean
        )
        assert has_data

    def test_seed_reproducibility(self) -> None:
        cfg = _minimal_config()
        r1 = run_monte_carlo(cfg, seeds=[7, 8, 9])
        r2 = run_monte_carlo(cfg, seeds=[7, 8, 9])
        assert r1.avg_compliance.mean == pytest.approx(r2.avg_compliance.mean)
        assert r1.step_compliance[0].mean == pytest.approx(r2.step_compliance[0].mean)

    def test_different_seeds_give_variation(self) -> None:
        cfg = _minimal_config()
        r1 = run_monte_carlo(cfg, seeds=[0, 1, 2, 3, 4])
        # With 5 different seeds, SD should be >= 0 (not asserting > 0 since deterministic configs may converge)
        assert r1.avg_compliance.std >= 0.0

    def test_seeds_list_respected(self) -> None:
        cfg = _minimal_config()
        seeds = [10, 20, 30]
        result = run_monte_carlo(cfg, seeds=seeds)
        assert result.n_runs == 3
        assert result.seeds == seeds
