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
    FALSE_POSITIVE_RATE_MEAN = "false_positive_rate_mean"
    FALSE_POSITIVE_RATE_STD = "false_positive_rate_std"
    DETECTION_RATE_MEAN = "detection_rate_mean"
    DETECTION_RATE_STD = "detection_rate_std"


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
    false_positive_rate: float
    detection_rate: float  # NaN if no audited violators


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
    false_positive_rate: MetricStats  # audits on compliant / total audits
    detection_rate: MetricStats  # caught / audits on violators

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
        """Return first param value where mean avg_compliance >= threshold.

        Args:
            threshold: Compliance fraction to consider as 'achieved' (default 0.95).

        Returns:
            First param_value meeting the threshold, or None if never reached.
        """
        for pt in self.points:
            if pt.result.avg_compliance.mean >= threshold:
                return pt.param_value
        return None
