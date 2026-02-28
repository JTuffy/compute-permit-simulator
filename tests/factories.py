"""Test data factories for generating valid schema objects."""

from typing import Any

from compute_permit_sim.schemas import (
    AgentSnapshot,
    AuditConfig,
    LabConfig,
    MarketConfig,
    MarketSnapshot,
    ScenarioConfig,
)


def create_agent_snapshot(
    id: int = 1,
    is_compliant: bool = True,
    **kwargs: Any,
) -> AgentSnapshot:
    """Create a valid AgentSnapshot with overrideable defaults."""
    defaults = {
        "compute_capacity": 1e25,
        "planned_training_flops": 1e25,
        "used_training_flops": 1e25,
        "reported_training_flops": 1e25,
        "has_permit": True,
        "was_audited": False,
        "was_caught": False,
        "penalty_amount": 0.0,
        "economic_value": 100.0,
        "risk_profile": 1.0,
    }
    data = {**defaults, **kwargs}
    return AgentSnapshot(id=id, is_compliant=is_compliant, **data)


def create_market_snapshot(
    price: float = 1.0, supply: float = 100.0, **kwargs: Any
) -> MarketSnapshot:
    """Create a valid MarketSnapshot."""
    return MarketSnapshot(price=price, supply=supply)


def create_scenario_config(
    name: str = "Test Scenario", **kwargs: Any
) -> ScenarioConfig:
    """Create a valid ScenarioConfig."""
    defaults = {
        "n_agents": 5,
        "steps": 10,
        "audit": AuditConfig(),
        "market": MarketConfig(permit_cap=100),
        "lab": LabConfig(),
    }
    data = {**defaults, **kwargs}
    return ScenarioConfig(name=name, **data)
