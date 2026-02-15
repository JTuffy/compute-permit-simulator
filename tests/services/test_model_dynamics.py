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
        high_prob=0.1,
        false_positive_rate=0.0,
        false_negative_rate=0.0,
        penalty_amount=1.0,
    )
    market = MarketConfig(token_cap=10, fixed_price=0.5)
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
    audit_low = audit.model_copy(update={"base_prob": 0.1, "high_prob": 0.1})
    comp_low = run_model_get_compliance(audit_low, market, lab)

    # High Audit: p=0.6, B=4.0. E[P] = 2.4. Gain=2.0 < 2.4. Comply.
    audit_high = audit.model_copy(update={"base_prob": 0.6, "high_prob": 0.6})
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
            "penalty_amount": 4.0,
            "base_prob": 0.2,
            "high_prob": 0.2,
            "false_negative_rate": 0.5,  # Meaningful FNR
        }
    )
    # Base effective p without backcheck:
    # p_s = (1-0.5)*0.2 + 0.5*0.2 = 0.2
    # E[P] = 0.2 * 4.0 = 0.8. Gain=2.0 > 0.8. Cheat.

    # Case 1: No Backcheck
    audit_no_bc = audit.model_copy(update={"backcheck_prob": 0.0})
    comp_no_bc = run_model_get_compliance(audit_no_bc, market, lab)

    # Case 2: High Backcheck
    # p_eff = 0.2 + (0.8)*0.9 = 0.2 + 0.72 = 0.92
    # E[P] = 0.92 * 4.0 = 3.68. Gain=2.0 < 3.68. Desist.
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
            "high_prob": 0.0,
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
