"""Unit tests for metrics service."""

from compute_permit_sim.services.metrics import (
    calculate_compliance,
    calculate_wealth_stats,
)


def test_calculate_compliance_empty() -> None:
    """Test compliance calculation with no agents."""
    assert calculate_compliance([]) == 0.0


def test_calculate_compliance_mixed(agent_snapshot_factory) -> None:
    """Test compliance calculation with mixed agents."""
    agents = [
        agent_snapshot_factory(id=1, is_compliant=True, wealth=10.0),
        agent_snapshot_factory(id=2, is_compliant=False, wealth=10.0),
        agent_snapshot_factory(id=3, is_compliant=True, wealth=10.0),
        agent_snapshot_factory(id=4, is_compliant=False, wealth=10.0),
    ]
    # 2/4 compliant = 0.5
    assert calculate_compliance(agents) == 0.5


def test_calculate_compliance_all_compliant(agent_snapshot_factory) -> None:
    """Test compliance with all agents compliant."""
    agents = [
        agent_snapshot_factory(id=1, is_compliant=True, wealth=10.0),
        agent_snapshot_factory(id=2, is_compliant=True, wealth=10.0),
    ]
    assert calculate_compliance(agents) == 1.0


def test_calculate_wealth_stats(agent_snapshot_factory) -> None:
    """Test wealth statistics calculation."""
    agents = [
        agent_snapshot_factory(id=1, is_compliant=True, wealth=100.0),
        agent_snapshot_factory(id=2, is_compliant=False, wealth=50.0),
        agent_snapshot_factory(id=3, is_compliant=True, wealth=25.0),
    ]
    # Compliant: 100 + 25 = 125
    # Non-compliant: 50
    comp_w, non_comp_w = calculate_wealth_stats(agents)
    assert comp_w == 125.0
    assert non_comp_w == 50.0


def test_calculate_wealth_stats_empty() -> None:
    """Test wealth stats with empty list."""
    assert calculate_wealth_stats([]) == (0.0, 0.0)
