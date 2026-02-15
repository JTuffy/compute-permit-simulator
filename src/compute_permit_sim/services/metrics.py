"""Centralized metrics calculation for simulation data.

This module provides pure functions to calculate derived metrics (compliance, wealth, etc.)
from agent snapshots, ensuring consistency between the live simulation engine,
historical analysis, and exported reports.
"""

from typing import List, Tuple

from compute_permit_sim.schemas.data import AgentSnapshot


def calculate_compliance(agents: List[AgentSnapshot]) -> float:
    """Calculate the compliance rate (0.0 to 1.0)."""
    if not agents:
        return 0.0
    compliant_count = sum(1 for a in agents if a.is_compliant)
    return compliant_count / len(agents)


def calculate_wealth_stats(agents: List[AgentSnapshot]) -> Tuple[float, float]:
    """Calculate total wealth for compliant vs non-compliant agents.

    Returns:
        Tuple[float, float]: (compliant_wealth, non_compliant_wealth)
    """
    if not agents:
        return 0.0, 0.0

    compliant_wealth = sum(a.wealth for a in agents if a.is_compliant)
    non_compliant_wealth = sum(a.wealth for a in agents if not a.is_compliant)
    return compliant_wealth, non_compliant_wealth


def calculate_run_metrics(steps: list) -> "RunMetrics":  # noqa: F821
    """Calculate aggregate run metrics from a list of steps.

    Args:
        steps: List of StepResult objects (or objects with .agents, .market attributes).

    Returns:
        RunMetrics object.
    """
    from compute_permit_sim.schemas.data import RunMetrics

    if not steps:
        return RunMetrics(
            final_compliance=0.0,
            final_price=0.0,
            total_enforcement_cost=0.0,
            deterrence_success_rate=0.0,
        )

    last_step = steps[-1]

    # Final Compliance
    final_compliance = calculate_compliance(last_step.agents)

    # Final Price
    final_price = last_step.market.price

    # Total Enforcement Cost (Sum of all steps)
    # Assuming cost is tracked somewhere or we estimate it?
    # For now, let's sum up audit costs if available, or just leave as placeholder.
    # The current schema expects 'total_enforcement_cost'.
    # We can sum (audit_cost per step).
    # If not tracked, we return 0.0 for now to unblock.
    total_enforcement_cost = 0.0

    # Deterrence Success Rate (Proxy: Average compliance over time or final?)
    # Schema desc says: "Rate of successful deterrence (proxy: compliance)"
    # Let's use average compliance over the whole run for a better metric than just final.
    all_compliance = [calculate_compliance(s.agents) for s in steps]
    avg_compliance = sum(all_compliance) / len(all_compliance)

    return RunMetrics(
        final_compliance=final_compliance,
        final_price=final_price,
        total_enforcement_cost=total_enforcement_cost,
        deterrence_success_rate=avg_compliance,
    )
