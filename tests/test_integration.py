from compute_permit_sim.infrastructure.model import ComputePermitModel
from compute_permit_sim.schemas import (
    AuditConfig,
    LabConfig,
    MarketConfig,
    ScenarioConfig,
)


def test_simulation_integration():
    """Run a minimal simulation for a few steps to check for crashes and basic logic."""
    audit_config = AuditConfig(
        base_prob=0.1,
        high_prob=0.5,
        false_positive_rate=0.05,
        false_negative_rate=0.1,
        penalty_amount=0.5,
        backcheck_prob=0.0,
    )
    market_config = MarketConfig(token_cap=5)
    lab_config = LabConfig()

    config = ScenarioConfig(
        name="Test Scenario",
        n_agents=10,
        steps=5,
        audit=audit_config,
        market=market_config,
        lab=lab_config,
        seed=42,
    )

    model = ComputePermitModel(config)

    for _ in range(3):
        model.step()

    # Check that data collection happened
    df = model.datacollector.get_model_vars_dataframe()
    assert len(df) == 3
    assert "Compliance_Rate" in df.columns
    assert "Price" in df.columns


def test_fixed_price_integration():
    """Run a simulation with fixed price market."""
    audit_config = AuditConfig(
        base_prob=0.1,
        high_prob=0.5,
        false_positive_rate=0.05,
        false_negative_rate=0.1,
        penalty_amount=0.5,
        backcheck_prob=0.0,
    )
    # Fixed price 1.0, effectively unlimited cap.
    market_config = MarketConfig(token_cap=100)
    market_config.set_fixed_price(1.0)
    lab_config = LabConfig()

    config = ScenarioConfig(
        name="Fixed Price Test",
        n_agents=5,
        steps=3,
        audit=audit_config,
        market=market_config,
        lab=lab_config,
    )

    model = ComputePermitModel(config)
    model.step()

    # Check if price was fixed
    df = model.datacollector.get_model_vars_dataframe()
    last_price = df["Price"].iloc[-1]
    assert last_price == 1.0

    # Check agents
    # Agents with value >= 1.0 should have permits
    # We seeded, but let's just check consistency
    for agent in model.agents:
        if hasattr(agent, "domain_agent"):  # Skip scheduler/other entities if any
            da = agent.domain_agent
            if da.gross_value >= 1.0:
                assert da.has_permit is True
            else:
                assert da.has_permit is False
