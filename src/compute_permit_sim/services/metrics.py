"""Centralized metrics calculation for simulation data.

Pure functions over typed schema objects — consistent across the live
simulation engine, historical analysis, and exported reports.
"""

from compute_permit_sim.schemas.data import AgentSnapshot, RunMetrics, StepResult


def calculate_compliance(agents: list[AgentSnapshot]) -> float:
    """Compliance rate (0.0 to 1.0) across a set of agent snapshots."""
    if not agents:
        return 0.0
    compliant_count = sum(1 for a in agents if a.is_compliant)
    return compliant_count / len(agents)


def calculate_run_metrics(steps: list[StepResult]) -> RunMetrics:
    """Aggregate run-level metrics from a list of completed steps.

    Uses average compliance over all steps as the deterrence_success_rate
    proxy — more representative than final-step compliance alone.

    Args:
        steps: Ordered list of per-step snapshots (empty list returns zero metrics).

    Returns:
        RunMetrics with final compliance, final price, and average compliance.
    """
    if not steps:
        return RunMetrics(
            final_compliance=0.0,
            final_price=0.0,
            deterrence_success_rate=0.0,
        )

    last_step = steps[-1]
    final_compliance = calculate_compliance(last_step.agents)
    final_price = last_step.market.price
    all_compliance = [calculate_compliance(s.agents) for s in steps]
    avg_compliance = sum(all_compliance) / len(all_compliance)

    return RunMetrics(
        final_compliance=final_compliance,
        final_price=final_price,
        deterrence_success_rate=avg_compliance,
    )
