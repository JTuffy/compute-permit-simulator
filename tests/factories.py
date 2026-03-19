"""Test data factories for generating valid schema objects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from compute_permit_sim.schemas.batch import GridSweepResult

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
        "caught_source": None,
        "audit_coefficient": 1.0,
        "cumulative_capability": 0.0,
        "bid_price": 0.0,
        "permits_wanted": 0,
        "racing_factor": 1.0,
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


def create_grid_sweep_result(
    n_x: int = 3,
    n_y: int = 2,
    scenario_name: str = "Test Scenario",
) -> "GridSweepResult":
    """Create a minimal GridSweepResult for testing — no simulation run needed."""
    from compute_permit_sim.schemas.batch import GridSweepResult

    x_values = [float(i) * 0.1 for i in range(1, n_x + 1)]
    y_values = [float(j) * 10.0 for j in range(1, n_y + 1)]
    # grid[y_idx][x_idx] = synthetic compliance value in [0, 1]
    grid = [
        [float(y_idx * n_x + x_idx) / (n_x * n_y) for x_idx in range(n_x)]
        for y_idx in range(n_y)
    ]
    return GridSweepResult(
        scenario_name=scenario_name,
        param_x_path="audit.base_prob",
        param_x_label="Base Audit Probability",
        param_y_path="collateral_amount",
        param_y_label="Collateral K (M$)",
        config=create_scenario_config(name=scenario_name),
        x_values=x_values,
        y_values=y_values,
        grid=grid,
        n_runs=5,
    )
