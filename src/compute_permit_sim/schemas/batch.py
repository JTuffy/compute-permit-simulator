"""Batch analysis schemas: Monte Carlo and parameter sweep results.

All dataclasses are frozen for immutability and safe use as reactive
state in the Solara UI layer.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from uuid import uuid4

from compute_permit_sim.schemas.config import ScenarioConfig


class BatchColumnNames:
    """Column-name constants for batch export CSVs.

    Mirrors the ColumnNames convention from ``schemas.columns``
    so consumers can reference these as typed constants rather
    than free-form strings.
    """

    # Identifiers
    SCENARIO = "scenario"
    SEED = "seed"
    STEP = "step"
    PARAM_PATH = "param_path"
    PARAM_VALUE = "param_value"
    N_RUNS = "n_runs"

    # 2-D grid sweep — per-axis identifiers
    PARAM_X_PATH = "param_x_path"
    PARAM_X_VALUE = "param_x_value"
    PARAM_Y_PATH = "param_y_path"
    PARAM_Y_VALUE = "param_y_value"

    # Compliance
    COMPLIANCE_RATE = "compliance_rate"
    N_VIOLATORS = "n_violators"
    AVG_COMPLIANCE_MEAN = "avg_compliance_mean"
    AVG_COMPLIANCE_STD = "avg_compliance_std"
    FINAL_COMPLIANCE_MEAN = "final_compliance_mean"
    P10_COMPLIANCE = "p10_compliance"
    P90_COMPLIANCE = "p90_compliance"
    PCT_RUNS_FULL_COMPLIANCE = "pct_runs_full_compliance"

    # Market
    MARKET_PRICE = "market_price"
    AVG_PRICE_MEAN = "avg_price_mean"
    AVG_PRICE_STD = "avg_price_std"

    # Payoffs
    NET_PAYOFF = "net_payoff"
    AVG_NET_PAYOFF_MEAN = "avg_net_payoff_mean"
    AVG_NET_PAYOFF_STD = "avg_net_payoff_std"
    PAYOFF_COMPLIANT_MEAN = "payoff_compliant_mean"
    PAYOFF_COMPLIANT_STD = "payoff_compliant_std"
    PAYOFF_VIOLATOR_MEAN = "payoff_violator_mean"
    PAYOFF_VIOLATOR_STD = "payoff_violator_std"

    # Audit
    AUDIT_RATE = "audit_rate"
    AUDIT_RATE_MEAN = "audit_rate_mean"
    AUDIT_RATE_STD = "audit_rate_std"
    COMPLIANT_AUDIT_FRACTION_MEAN = "compliant_audit_fraction_mean"
    COMPLIANT_AUDIT_FRACTION_STD = "compliant_audit_fraction_std"
    CATCH_RATE_MEAN = "catch_rate_mean"
    CATCH_RATE_STD = "catch_rate_std"


@dataclass(frozen=True)
class PerSeedResult:
    """Raw scalar summary for a single simulation seed.

    Stored optionally in ``MonteCarloResult.raw_seeds`` when ``store_raw=True``
    is passed to ``run_monte_carlo()``. Enables full per-seed CSV export and
    post-hoc analysis without re-running simulations.
    """

    seed: int
    avg_compliance: float
    final_compliance: float
    avg_price: float
    avg_net_payoff: float
    avg_payoff_compliant: float  # NaN if no compliant labs
    avg_payoff_violator: float  # NaN if no violators
    audit_rate: float
    compliant_audit_fraction: float
    catch_rate: float  # NaN if no audited violators


@dataclass(frozen=True)
class MetricStats:
    """Mean, standard deviation, and 95% CI for a single metric across N runs."""

    mean: float
    std: float
    ci_low: float
    ci_high: float
    n: int

    def __str__(self) -> str:
        if self.std < 1e-9:
            return f"{self.mean:.3f}"
        return f"{self.mean:.3f} ± {self.std:.3f}"

    @classmethod
    def from_values(cls, values: list[float]) -> "MetricStats":
        """Compute MetricStats from a list of raw per-run values."""
        n = len(values)
        if n == 0:
            return cls(mean=0.0, std=0.0, ci_low=0.0, ci_high=0.0, n=0)
        mean = statistics.mean(values)
        std = statistics.stdev(values) if n > 1 else 0.0
        margin = 2.0 * std / math.sqrt(n)
        return cls(mean=mean, std=std, ci_low=mean - margin, ci_high=mean + margin, n=n)

    @classmethod
    def nan(cls) -> "MetricStats":
        """Sentinel for metrics not applicable in a given run (e.g. no violators)."""
        return cls(
            mean=float("nan"),
            std=float("nan"),
            ci_low=float("nan"),
            ci_high=float("nan"),
            n=0,
        )


@dataclass(frozen=True)
class MonteCarloResult:
    """Aggregated results from N runs of a single scenario configuration.

    All fields represent cross-seed statistics (mean ± SD ± 95% CI).

    Step-level trajectory fields contain one MetricStats per simulation step,
    enabling convergence and equilibrium analysis.
    """

    scenario_name: str
    n_runs: int
    seeds: list[int]
    # Base config used for the run — required for config dialog + save-as-template
    config: ScenarioConfig

    # --- Aggregate compliance ---
    avg_compliance: MetricStats  # mean over all steps, then over seeds
    final_compliance: MetricStats  # compliance at last step
    p10_compliance: float  # 10th percentile of per-seed avg compliance
    p90_compliance: float  # 90th percentile of per-seed avg compliance
    pct_runs_full_compliance: float  # fraction of seeds that ever hit 100%

    # --- Step-level trajectory (list[step] → MetricStats across seeds) ---
    step_compliance: list[MetricStats]  # per-step mean compliance ± SD
    step_n_violators: list[MetricStats]  # per-step violator count ± SD

    # --- Market ---
    avg_price: MetricStats
    final_price: MetricStats

    # --- Economic ---
    avg_net_payoff: MetricStats  # all labs, all steps
    payoff_compliant: MetricStats  # compliant labs only
    payoff_violator: MetricStats  # violating labs only (nan if none)

    # --- Audit burden ---
    audit_rate: MetricStats  # audits / total lab-steps
    compliant_audit_fraction: MetricStats  # audits on compliant / total audits
    catch_rate: MetricStats  # caught / audits on violators

    # --- Raw per-seed data (optional, set store_raw=True in run_monte_carlo) ---
    raw_seeds: list[PerSeedResult] = field(default_factory=list)
    # Seeds that raised exceptions during the run — non-empty signals data quality issues
    failed_seeds: list[int] = field(default_factory=list)
    # Short unique identifier matching SimulationRun.sim_id convention
    id: str = field(default_factory=lambda: str(uuid4())[:8])


@dataclass(frozen=True)
class SweepPoint:
    """One point in a parameter sweep: a specific param value and its MC result."""

    param_value: float
    result: MonteCarloResult


@dataclass(frozen=True)
class SweepResult:
    """Results of a 1D parameter sweep over a scenario."""

    scenario_name: str
    param_path: str  # e.g. "audit.base_prob"
    param_label: str  # human-readable, e.g. "Base Audit Rate π₀"
    # Base config the sweep started from — required for config dialog + save-as-template
    config: ScenarioConfig
    points: list[SweepPoint] = field(default_factory=list)
    # Short unique identifier matching SimulationRun.sim_id convention
    id: str = field(default_factory=lambda: str(uuid4())[:8])

    def compliance_series(self) -> list[tuple[float, float, float]]:
        """Returns list of (param_value, mean_compliance, std_compliance)."""
        return [
            (p.param_value, p.result.avg_compliance.mean, p.result.avg_compliance.std)
            for p in self.points
        ]

    def tipping_point(self, threshold: float = 0.95) -> float | None:
        """Return the boundary param value where mean avg_compliance crosses threshold.

        Direction-aware: detects whether compliance rises or falls with the
        parameter and returns the appropriate boundary.

        - Upward sweep (compliance rises with param, e.g. audit rate):
          returns first param_value where compliance >= threshold.
        - Downward sweep (compliance falls with param, e.g. permit price):
          returns last param_value where compliance >= threshold,
          i.e. the ceiling before compliance drops below threshold.

        Args:
            threshold: Compliance fraction to consider as the boundary
                (default 0.95).

        Returns:
            Boundary param_value, or None if compliance never reaches threshold.
        """
        if not self.points:
            return None

        means = [pt.result.avg_compliance.mean for pt in self.points]

        # Detect direction: compare first and last point
        # Use a simple heuristic: if the last mean < first mean, it's a downward sweep.
        is_downward = means[-1] < means[0]

        if is_downward:
            # Last point where compliance is still at or above the threshold
            result = None
            for pt in self.points:
                if pt.result.avg_compliance.mean >= threshold:
                    result = pt.param_value
                else:
                    break  # First drop below threshold — stop here
            return result
        else:
            # First point where compliance reaches or exceeds the threshold
            for pt in self.points:
                if pt.result.avg_compliance.mean >= threshold:
                    return pt.param_value
            return None


@dataclass(frozen=True)
class GridSweepResult:
    """Results of a 2D joint-sensitivity parameter sweep over a scenario.

    Stores mean compliance at every (x, y) grid cell.

    Attributes:
        grid: ``grid[y_idx][x_idx]`` = mean compliance fraction (0–1)
              over ``n_runs`` seeds at parameter values
              ``(x_values[x_idx], y_values[y_idx])``.
    """

    scenario_name: str
    param_x_path: str  # e.g. "audit.base_prob"
    param_x_label: str  # human-readable, e.g. "Base Audit Probability"
    param_y_path: str  # e.g. "collateral_amount"
    param_y_label: str  # human-readable, e.g. "Collateral K (M$)"
    config: ScenarioConfig
    x_values: list[float]  # ordered x-axis values
    y_values: list[float]  # ordered y-axis values
    grid: list[list[float]]  # [y_idx][x_idx] = mean compliance in [0, 1]
    n_runs: int
    # Short unique identifier matching SimulationRun.sim_id convention
    id: str = field(default_factory=lambda: str(uuid4())[:8])

    def compliance_at(self, x: float, y: float) -> float | None:
        """Return mean compliance for an exact (x, y) cell, or None if not found."""
        try:
            x_idx = self.x_values.index(x)
            y_idx = self.y_values.index(y)
        except ValueError:
            return None
        return self.grid[y_idx][x_idx]

    @property
    def compliance_min(self) -> float:
        """Minimum mean compliance across all grid cells."""
        return min(v for row in self.grid for v in row)

    @property
    def compliance_max(self) -> float:
        """Maximum mean compliance across all grid cells."""
        return max(v for row in self.grid for v in row)
