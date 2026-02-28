from compute_permit_sim.schemas import (
    AuditConfig,
    LabConfig,
    MarketConfig,
    ScenarioConfig,
)
from compute_permit_sim.services.mesa_model import ComputePermitModel


def get_base_configs():
    """Helper to get default configurations."""
    audit = AuditConfig(
        base_prob=0.1,
        false_positive_rate=0.0,
        false_negative_rate=0.0,
        penalty_amount=1.0,
    )
    market = MarketConfig(permit_cap=10, fixed_price=0.5)
    lab = LabConfig(
        economic_value_min=1.0,
        economic_value_max=1.0,
        risk_profile_min=1.0,
        risk_profile_max=1.0,
    )
    return audit, market, lab


def run_model_get_compliance(audit, market, lab, steps=1):
    """Helper function to run a model for N steps and return the final compliance rate.

    Args:
        audit: Auditor configuration.
        market: Market configuration.
        lab: Lab configuration.
        steps: Number of steps to run.

    Returns:
        Final compliance rate as a float.
    """
    config = ScenarioConfig(
        name="Test",
        n_agents=10,
        steps=steps,
        audit=audit,
        market=market,
        lab=lab,
        seed=42,
    )
    model = ComputePermitModel(config)
    for _ in range(steps):
        model.step()
    return model.datacollector.get_model_vars_dataframe()["Compliance_Rate"].iloc[-1]


def test_higher_audit_rate_higher_compliance():
    """Check higher base audit rate leads to higher compliance rate."""
    audit, market, lab = get_base_configs()
    # Setup: High incentive to cheat.
    # fixed_price=2.0 (Gain from cheating is 2.0).
    # We need p*B > 2.0 to deter.
    market = market.model_copy(update={"fixed_price": 2.0})
    audit = audit.model_copy(
        update={"penalty_amount": 4.0}
    )  # B=4.0, need to add this as function to that class

    # Case 1: Low Audit. p=0.1. Expected Penalty = 0.1 * 4.0 = 0.4 < 2.0. Cheat.
    audit_low = audit.model_copy(update={"base_prob": 0.1})
    comp_low = run_model_get_compliance(audit_low, market, lab)

    # High Audit: p=0.6, B=4.0. E[P] = 2.4. Gain=2.0 < 2.4. Comply.
    audit_high = audit.model_copy(update={"base_prob": 0.6})
    comp_high = run_model_get_compliance(audit_high, market, lab)

    assert comp_high > comp_low
    assert comp_low == 0.0  # All cheat
    assert comp_high == 1.0  # All desist (compliant)


def test_higher_backcheck_rate_higher_compliance():
    """Check higher backcheck rate leads to higher compliance rate (non-zero FNR)."""
    audit, market, lab = get_base_configs()
    # Price > Value so they rely on cheating vs desisting
    market = market.model_copy(update={"fixed_price": 2.0})
    audit = audit.model_copy(
        update={
            "penalty_amount": 10.0,
            "base_prob": 0.2,
            "false_negative_rate": 0.8,  # Meaningful FNR
        }
    )
    # Base effective p without backcheck:
    # p_catch = (1-0.8) + 0.8*0.0 = 0.2
    # E[P] = 0.2 * 0.2 * 10.0 = 0.4. Gain=1.0 > 0.4. Cheat.

    # Case 1: No Backcheck
    audit_no_bc = audit.model_copy(update={"backcheck_prob": 0.0})
    comp_no_bc = run_model_get_compliance(audit_no_bc, market, lab)

    # Case 2: High Backcheck
    # p_catch = 0.2 + (0.8)*0.9 = 0.2 + 0.72 = 0.92
    # E[P] = 0.2 * 0.92 * 10.0 = 1.84. Gain=1.0 < 1.84. Desist.
    audit_bc = audit.model_copy(update={"backcheck_prob": 0.9})
    comp_bc = run_model_get_compliance(audit_bc, market, lab)

    assert comp_bc > comp_no_bc


def test_zero_enforcement_zero_compliance():
    """Zero audit rate and zero reputation sensitivity lead to zero compliance rate."""
    audit, market, lab = get_base_configs()
    # Price > Value to prevent buying
    market = market.model_copy(update={"fixed_price": 2.0})
    # Zero enforcement
    audit = audit.model_copy(
        update={
            "base_prob": 0.0,
            "backcheck_prob": 0.0,
            "penalty_amount": 10.0,  # Irrelevant if p=0
        }
    )
    lab = lab.model_copy(update={"reputation_sensitivity": 0.0})

    comp = run_model_get_compliance(audit, market, lab)
    assert comp == 0.0


def test_high_racing_factor_zero_compliance():
    """Very high racing factor with max supply leads to zero compliance rate."""
    audit, market, lab = get_base_configs()

    market = market.model_copy(update={"fixed_price": 2.0})  # Price > Value (1.0)
    lab = lab.model_copy(
        update={
            "economic_value_min": 1.0,
            "economic_value_max": 1.0,
            "capability_value": 1.0,
            "racing_factor": 1000.0,  # Huge gain from cheating
        }
    )
    # Even with reasonable enforcement
    audit = audit.model_copy(update={"base_prob": 0.5, "penalty_amount": 1.0})

    comp = run_model_get_compliance(audit, market, lab)
    assert comp == 0.0


def test_per_firm_penalty_deters_individual():
    """Test that setting a per-firm penalty_amount affects deterrence individually."""
    audit, market, lab = get_base_configs()
    market = market.model_copy(update={"fixed_price": 2.0})
    # Global penalty is 0.0, base_prob is 1.0 (100% catch rate)
    audit = audit.model_copy(
        update={
            "base_prob": 1.0,
            "penalty_amount": 0.0,
        }
    )
    config = ScenarioConfig(
        name="Test Per Firm Penalty",
        n_agents=2,
        steps=1,
        audit=audit,
        market=market,
        lab=lab,
        seed=42,
    )
    from compute_permit_sim.services.mesa_model import ComputePermitModel

    model = ComputePermitModel(config)

    # Override penalty_amount on the domain agents directly
    # Firm 1: Gain=1.0, P=1.0, Penalty=0.0 -> E[P]=0.0. Will cheat.
    # Firm 2: Gain=1.0, P=1.0, Penalty=5.0 -> E[P]=5.0. Will comply.
    mesa_agents = [a for a in model.agents if hasattr(a, "domain_agent")]
    mesa_agents[0].domain_agent.penalty_amount = 0.0
    mesa_agents[1].domain_agent.penalty_amount = 5.0

    model.step()

    assert mesa_agents[0].domain_agent.is_compliant is False
    assert mesa_agents[1].domain_agent.is_compliant is True
