"""Advanced integration tests for complex simulation scenarios."""

from compute_permit_sim.schemas import (
    AuditConfig,
    LabConfig,
    MarketConfig,
    ScenarioConfig,
)
from compute_permit_sim.services.model_wrapper import ComputePermitModel


def get_base_configs():
    """Helper to get default configurations."""
    audit = AuditConfig(
        base_prob=0.1,
        high_prob=0.1,
        false_positive_rate=0.0,
        false_negative_rate=0.0,
        penalty_amount=1.0,
        backcheck_prob=0.0,
        whistleblower_prob=0.0,
    )
    market = MarketConfig(token_cap=10, fixed_price=None)
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


def test_whistleblower_increases_compliance():
    """Test that higher whistleblower rate increases compliance.

    Condition:
    - Lab Value (1.0) < Price (2.0) -> Won't buy permit.
    - Gain from Cheating = 1.0.
    - Penalty = 4.0.
    - Base Audit Prob = 0.1 -> E[P] = 0.4 < Gain -> Cheat.
    - Whistleblower adds detection probability, pushing E[P] > Gain.
    """
    audit, market, lab = get_base_configs()
    market = market.model_copy(update={"fixed_price": 2.0})
    audit = audit.model_copy(
        update={"penalty_amount": 4.0, "base_prob": 0.1, "high_prob": 0.1}
    )

    # Baseline: Low detection -> Cheat (0% Compliance)
    comp_base = run_model_get_compliance(audit, market, lab)
    assert comp_base == 0.0

    # With Whistleblower: Higher detection -> Deterred (100% Compliance)
    audit_wb = audit.model_copy(update={"whistleblower_prob": 0.5})
    comp_wb = run_model_get_compliance(audit_wb, market, lab)

    assert comp_wb > comp_base
    assert comp_wb == 1.0


def test_higher_backcheck_reduces_false_compliance():
    """Test that higher backcheck probability increases deterrence.

    Setup:
    - High Price (2.0) > Value (1.0).
    - Moderate Base Audit (0.1).
    """
    audit, market, lab = get_base_configs()
    market.set_fixed_price(2.0)
    audit = audit.model_copy(
        update={"penalty_amount": 4.0, "base_prob": 0.1, "high_prob": 0.1}
    )

    # Case 1: Low Backcheck (0.1). E[P] insufficient -> All Cheat.
    audit_low = audit.model_copy(update={"backcheck_prob": 0.1})
    comp_low = run_model_get_compliance(audit_low, market, lab)
    assert comp_low == 0.0

    # Case 2: High Backcheck (0.8). E[P] sufficient -> All Comply.
    audit_high = audit.model_copy(update={"backcheck_prob": 0.8})
    comp_high = run_model_get_compliance(audit_high, market, lab)

    assert comp_high > comp_low
    assert comp_high == 1.0


def test_audit_capacity_constraint():
    """Test that max_audits_per_step limits penalized agents."""
    audit, market, lab = get_base_configs()
    market.set_fixed_price(2.0)

    # 100% detection + low penalty so everyone cheats but audits capped
    audit = audit.model_copy(
        update={
            "base_prob": 1.0,
            "high_prob": 1.0,
            "max_audits_per_step": 2,
            "penalty_amount": 0.5,
        }
    )

    config = ScenarioConfig(
        name="Test Capacity",
        n_agents=10,
        steps=1,
        audit=audit,
        market=market,
        lab=lab,
        seed=42,
    )
    model = ComputePermitModel(config)
    model.step()

    # Verify exactly 2 agents were caught and fined
    fined_agents = [a for a in model.agents if a.last_audit_status["penalty"] > 0]
    assert len(fined_agents) == 2


def test_audit_targeting_efficiency():
    """Test that higher audit coefficient improves compliance.

    Scenario:
    - Agent values in range [0.8, 2.0].
    - Base audit parameters insufficient to deter high-value agents.
    """
    audit, market, lab = get_base_configs()
    market.set_fixed_price(3.0)
    audit = audit.model_copy(
        update={"penalty_amount": 4.0, "base_prob": 0.1, "high_prob": 0.1}
    )

    # Case 1: Uniform Audit (coeff=1.0).
    # E[P] = 0.4. Insufficient for Value > 0.4.
    # Since Value range is [0.8, 2.0], everyone cheats.
    lab_uniform = lab.model_copy(
        update={
            "economic_value_min": 0.8,
            "economic_value_max": 2.0,
            "audit_coefficient": 1.0,
        }
    )
    comp_uniform = run_model_get_compliance(audit, market, lab_uniform)
    assert comp_uniform == 0.0

    # Case 2: Targeted Audit (coeff=6.0).
    # p_eff scales by 6.0 -> E[P] increases dramatically.
    # Should deter even High Value agents (2.0).
    lab_targeted = lab_uniform.model_copy(update={"audit_coefficient": 6.0})
    comp_targeted = run_model_get_compliance(audit, market, lab_targeted)

    assert comp_targeted == 1.0
