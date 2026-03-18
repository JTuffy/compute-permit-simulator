"""Monte Carlo runner for the Compute Permit Simulator.

Runs a scenario N times with different seeds and aggregates results into
per-seed statistics (mean, SD, 95% CI) and per-step trajectories.

Usage:
    from compute_permit_sim.services.monte_carlo import run_monte_carlo
    result = run_monte_carlo(config, n_runs=50)
    print(result.avg_compliance)       # MetricStats(mean=0.30, std=0.00, ...)
    print(result.step_compliance[0])   # MetricStats for step 1
"""

from __future__ import annotations

import logging
import math
from typing import Callable, NamedTuple

from compute_permit_sim.schemas.batch import (
    MetricStats,
    MonteCarloResult,
    PerSeedResult,
)
from compute_permit_sim.schemas.config import ScenarioConfig
from compute_permit_sim.services.mesa_model import ComputePermitModel, MesaLab

# ---------------------------------------------------------------------------
# Internal per-run result (not exposed externally)
# ---------------------------------------------------------------------------


class _RunResult(NamedTuple):
    """All per-run data needed to aggregate into MonteCarloResult."""

    avg_compliance: float
    final_compliance: float
    avg_price: float
    final_price: float
    avg_net_payoff: float

    # Per-step trajectories — length == config.steps
    step_compliance: list[float]  # compliance rate per step
    step_n_violators: list[int]  # violator count per step

    # Split payoffs
    avg_payoff_compliant: float  # NaN if no compliant labs this run
    avg_payoff_violator: float  # NaN if no violators this run

    # Audit burden
    audit_rate: float
    compliant_audit_fraction: float  # audits on compliant / total audits
    detection_rate_given_audit: float  # NaN if 0 audited violators


def _run_once(config: ScenarioConfig, seed: int) -> _RunResult:
    """Execute one full simulation run; return all raw metrics."""
    config_seeded = config.model_copy(update={"seed": seed})
    model = ComputePermitModel(config=config_seeded)

    step_compliance: list[float] = []
    step_prices: list[float] = []
    step_n_violators: list[int] = []

    all_payoffs: list[float] = []
    compliant_payoffs: list[float] = []
    violator_payoffs: list[float] = []

    total_audits = 0
    audits_on_compliant = 0
    audits_on_violators = 0
    violations_caught = 0
    total_lab_steps = 0

    for _ in range(config.steps):
        model.step()

        mesa_labs = [a for a in model.agents if isinstance(a, MesaLab)]
        clearing_price = model.market.current_price

        n_compliant = sum(1 for a in mesa_labs if a.domain_agent.is_compliant)
        n_violators = len(mesa_labs) - n_compliant
        compliance_rate = n_compliant / len(mesa_labs) if mesa_labs else 0.0

        step_compliance.append(compliance_rate)
        step_prices.append(clearing_price)
        step_n_violators.append(n_violators)
        total_lab_steps += len(mesa_labs)

        for ml in mesa_labs:
            d = ml.domain_agent
            s = ml.last_step

            gross = d.economic_value if s.ran else 0.0
            permit_cost = clearing_price * d.permits_held
            collateral_cost = config.collateral_amount if s.collateral_seized else 0.0
            net = gross - permit_cost - s.penalty - collateral_cost

            all_payoffs.append(net)
            if d.is_compliant:
                compliant_payoffs.append(net)
            else:
                violator_payoffs.append(net)

            if s.audited:
                total_audits += 1
                if d.is_compliant:
                    audits_on_compliant += 1
                else:
                    audits_on_violators += 1
                    if s.caught:
                        violations_caught += 1

    avg_compliance = sum(step_compliance) / len(step_compliance)
    avg_price = sum(step_prices) / len(step_prices)
    avg_net_payoff = sum(all_payoffs) / len(all_payoffs) if all_payoffs else 0.0
    avg_payoff_compliant = (
        sum(compliant_payoffs) / len(compliant_payoffs)
        if compliant_payoffs
        else float("nan")
    )
    avg_payoff_violator = (
        sum(violator_payoffs) / len(violator_payoffs)
        if violator_payoffs
        else float("nan")
    )

    return _RunResult(
        avg_compliance=avg_compliance,
        final_compliance=step_compliance[-1],
        avg_price=avg_price,
        final_price=step_prices[-1],
        avg_net_payoff=avg_net_payoff,
        step_compliance=step_compliance,
        step_n_violators=step_n_violators,
        avg_payoff_compliant=avg_payoff_compliant,
        avg_payoff_violator=avg_payoff_violator,
        audit_rate=total_audits / total_lab_steps if total_lab_steps else 0.0,
        compliant_audit_fraction=(
            audits_on_compliant / total_audits if total_audits else 0.0
        ),
        detection_rate_given_audit=(
            violations_caught / audits_on_violators
            if audits_on_violators
            else float("nan")
        ),
    )


# ---------------------------------------------------------------------------
# Trajectory aggregation
# ---------------------------------------------------------------------------


def _trajectory_stats(
    runs: list[_RunResult],
    n_steps: int,
    extractor: Callable[[_RunResult, int], float],
) -> list[MetricStats]:
    """Build per-step MetricStats for any per-step field across all runs."""
    return [
        MetricStats.from_values([extractor(r, step_idx) for r in runs])
        for step_idx in range(n_steps)
    ]


# ---------------------------------------------------------------------------
# Percentile helpers (stdlib only)
# ---------------------------------------------------------------------------


def _percentile(values: list[float], p: float) -> float:
    """Compute the p-th percentile (0-100) of a sorted or unsorted list."""
    if not values:
        return float("nan")
    sorted_v = sorted(values)
    n = len(sorted_v)
    idx = (p / 100) * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    frac = idx - lo
    return sorted_v[lo] * (1 - frac) + sorted_v[hi] * frac


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_monte_carlo(
    config: ScenarioConfig,
    n_runs: int = 50,
    seeds: list[int] | None = None,
    store_raw: bool = False,
) -> MonteCarloResult:
    """Run a scenario N times and return aggregated metrics with trajectories.

    Args:
        config: Scenario configuration. The ``seed`` field is overridden per run.
        n_runs: Number of independent replications. Ignored if ``seeds`` is provided.
        seeds: Explicit list of seeds. If provided, ``n_runs`` is ignored and
               ``len(seeds)`` runs are executed.
        store_raw: If True, per-seed scalar summaries are stored in
                   ``MonteCarloResult.raw_seeds``.  Default False keeps memory lean.

    Returns:
        MonteCarloResult with aggregate stats, trajectories, and optionally raw seeds.
    """
    run_seeds = seeds if seeds is not None else list(range(n_runs))
    n_steps = config.steps

    raw: list[_RunResult] = []
    failed_seeds: list[int] = []
    for seed in run_seeds:
        try:
            raw.append(_run_once(config, seed))
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning(
                "MC seed %d failed: %s", seed, exc, exc_info=True
            )
            failed_seeds.append(seed)

    if not raw:
        raise RuntimeError(
            f"All {len(run_seeds)} seeds failed — check scenario config."
        )

    actual_n = len(raw)

    # Per-seed compliance averages (for percentile computation)
    per_seed_compliance = [r.avg_compliance for r in raw]

    # Fraction of seeds that ever hit full compliance in the final step
    pct_full = sum(1 for r in raw if r.final_compliance >= 1.0) / actual_n

    # Payoffs — filter NaN for violator stats
    clean_violator = [
        r.avg_payoff_violator for r in raw if not math.isnan(r.avg_payoff_violator)
    ]
    clean_compliant = [
        r.avg_payoff_compliant for r in raw if not math.isnan(r.avg_payoff_compliant)
    ]

    return MonteCarloResult(
        scenario_name=config.name,
        n_runs=actual_n,
        seeds=list(run_seeds),
        config=config,
        avg_compliance=MetricStats.from_values([r.avg_compliance for r in raw]),
        final_compliance=MetricStats.from_values([r.final_compliance for r in raw]),
        p10_compliance=_percentile(per_seed_compliance, 10),
        p90_compliance=_percentile(per_seed_compliance, 90),
        pct_runs_full_compliance=pct_full,
        step_compliance=_trajectory_stats(
            raw, n_steps, lambda r, i: r.step_compliance[i]
        ),
        step_n_violators=_trajectory_stats(
            raw, n_steps, lambda r, i: float(r.step_n_violators[i])
        ),
        avg_price=MetricStats.from_values([r.avg_price for r in raw]),
        final_price=MetricStats.from_values([r.final_price for r in raw]),
        avg_net_payoff=MetricStats.from_values([r.avg_net_payoff for r in raw]),
        payoff_compliant=(
            MetricStats.from_values(clean_compliant)
            if clean_compliant
            else MetricStats.nan()
        ),
        payoff_violator=(
            MetricStats.from_values(clean_violator)
            if clean_violator
            else MetricStats.nan()
        ),
        audit_rate=MetricStats.from_values([r.audit_rate for r in raw]),
        compliant_audit_fraction=MetricStats.from_values(
            [r.compliant_audit_fraction for r in raw]
        ),
        detection_rate_given_audit=(
            MetricStats.from_values(
                [
                    r.detection_rate_given_audit
                    for r in raw
                    if not math.isnan(r.detection_rate_given_audit)
                ]
            )
            if any(not math.isnan(r.detection_rate_given_audit) for r in raw)
            else MetricStats.nan()
        ),
        raw_seeds=[
            PerSeedResult(
                seed=s,
                avg_compliance=r.avg_compliance,
                final_compliance=r.final_compliance,
                avg_price=r.avg_price,
                avg_net_payoff=r.avg_net_payoff,
                avg_payoff_compliant=r.avg_payoff_compliant,
                avg_payoff_violator=r.avg_payoff_violator,
                audit_rate=r.audit_rate,
                compliant_audit_fraction=r.compliant_audit_fraction,
                detection_rate_given_audit=r.detection_rate_given_audit,
            )
            for s, r in zip(run_seeds, raw)
        ]
        if store_raw
        else [],
        failed_seeds=failed_seeds,
    )
