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
