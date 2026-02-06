"""Shared test fixtures."""

from typing import Callable

import pytest

from compute_permit_sim.schemas import (
    AuditConfig,
    LabConfig,
    MarketConfig,
    ScenarioConfig,
)
from compute_permit_sim.schemas.data import AgentSnapshot
from compute_permit_sim.services.model_wrapper import ComputePermitModel
from .factories import (
    create_agent_snapshot,
    create_market_snapshot,
    create_scenario_config,
)


@pytest.fixture
def agent_snapshot_factory() -> Callable[..., AgentSnapshot]:
    """Fixture that returns the agent snapshot factory function."""
    return create_agent_snapshot


@pytest.fixture
def scenario_config_factory() -> Callable[..., ScenarioConfig]:
    """Fixture that returns the scenario config factory function."""
    return create_scenario_config


@pytest.fixture
def basic_config() -> ScenarioConfig:
    """Return a basic scenario configuration."""
    return ScenarioConfig(
        steps=10,
        n_agents=5,
        market=MarketConfig(token_cap=100.0),
        audit=AuditConfig(
            audit_cost=1.0,
            base_prob=0.1,
            high_prob=0.5,
            penalty_amount=10.0,
        ),
        lab=LabConfig(
            economic_value_min=10.0,
            economic_value_max=20.0,
        ),
    )


@pytest.fixture
def model(basic_config: ScenarioConfig) -> ComputePermitModel:
    """Return an initialized model."""
    return ComputePermitModel(basic_config)
