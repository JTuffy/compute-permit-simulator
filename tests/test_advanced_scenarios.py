"""Advanced integration tests for complex simulation scenarios."""

from compute_permit_sim.schemas import (
    AuditConfig,
    LabConfig,
    MarketConfig,
    ScenarioConfig,
)
from compute_permit_sim.services.model_wrapper import ComputePermitModel


def get_base_configs():
    """Helper to get default configurations.

    Note: Uses normalized test units (not M$ scale) for predictable test behavior.
    All monetary values explicitly set to enable precise deterrence calculations.
    """
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
        capability_value=0.0,
        racing_factor=1.0,
        reputation_sensitivity=0.0,
        audit_coefficient=1.0,
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


def test_collateral_increases_deterrence():
    """Test that collateral increases deterrence (adds to expected loss).

    Ref: Christoph (2026) §2.5 — P_eff = K + phi
    Without collateral: expected_loss = p * (penalty + rep) * risk
    With collateral: expected_loss = p * (penalty + K + rep) * risk
    """
    audit, market, lab = get_base_configs()
    market = market.model_copy(update={"fixed_price": 2.0})
    # Low penalty + low audit = everyone cheats
    audit = audit.model_copy(
        update={"penalty_amount": 1.5, "base_prob": 0.2, "high_prob": 0.2}
    )
    # E[P] = 0.2 * 1.5 = 0.3 < Gain(1.0) → cheat
    comp_no_collateral = run_model_get_compliance(audit, market, lab)
    assert comp_no_collateral == 0.0

    # With collateral K=5.0: E[P] = 0.2 * (1.5 + 5.0) = 1.3 > Gain(1.0) → comply
    config = ScenarioConfig(
        name="Test Collateral",
        n_agents=10,
        steps=1,
        audit=audit,
        market=market,
        lab=lab,
        seed=42,
        collateral_amount=5.0,
    )
    model = ComputePermitModel(config)
    model.step()
    df = model.datacollector.get_model_vars_dataframe()
    comp_with_collateral = df["Compliance_Rate"].iloc[-1]

    assert comp_with_collateral > comp_no_collateral
    assert comp_with_collateral == 1.0


def test_collateral_seized_on_violation():
    """Test that collateral is seized when a violation is found.

    Setup: Everyone cheats, 100% audit, 100% detection.
    Collateral should be seized (not refunded).
    """
    audit, market, lab = get_base_configs()
    market.set_fixed_price(2.0)
    # Very low penalty so they still cheat even with collateral
    audit = audit.model_copy(
        update={
            "penalty_amount": 0.01,
            "base_prob": 1.0,
            "high_prob": 1.0,
        }
    )
    config = ScenarioConfig(
        name="Test Collateral Seized",
        n_agents=10,
        steps=1,
        audit=audit,
        market=market,
        lab=lab,
        seed=42,
        collateral_amount=10.0,
    )
    model = ComputePermitModel(config)
    model.step()

    # All agents should have collateral seized (caught cheating)
    for agent in model.agents:
        if hasattr(agent, "last_audit_status"):
            if agent.last_audit_status["caught"]:
                assert agent.last_audit_status["collateral_seized"] is True
                # Wealth should reflect: -collateral - penalty + economic_value
                # Collateral NOT refunded (seized)


def test_collateral_refunded_when_compliant():
    """Test that collateral is refunded when no violation found.

    Setup: High penalty so everyone complies. Collateral posted and returned.
    Net effect on wealth: zero from collateral.
    """
    audit, market, lab = get_base_configs()
    market.set_fixed_price(2.0)
    audit = audit.model_copy(
        update={"penalty_amount": 100.0, "base_prob": 1.0, "high_prob": 1.0}
    )
    config = ScenarioConfig(
        name="Test Collateral Refund",
        n_agents=10,
        steps=1,
        audit=audit,
        market=market,
        lab=lab,
        seed=42,
        collateral_amount=10.0,
    )
    model = ComputePermitModel(config)
    model.step()

    # All agents comply (high penalty) → collateral refunded
    for agent in model.agents:
        if hasattr(agent, "domain_agent"):
            # Collateral should be fully refunded (posted = 0 after step)
            assert agent.domain_agent.collateral_posted == 0.0
            # Collateral not seized
            assert agent.last_audit_status["collateral_seized"] is False


def test_zero_collateral_unchanged():
    """Test that zero collateral preserves existing behavior exactly."""
    audit, market, lab = get_base_configs()
    market.set_fixed_price(2.0)
    audit = audit.model_copy(
        update={"penalty_amount": 4.0, "base_prob": 0.1, "high_prob": 0.1}
    )
    # Run with explicit collateral_amount=0
    config = ScenarioConfig(
        name="Test No Collateral",
        n_agents=10,
        steps=1,
        audit=audit,
        market=market,
        lab=lab,
        seed=42,
        collateral_amount=0.0,
    )
    model = ComputePermitModel(config)
    model.step()

    # Behavior should be identical to default (no collateral effect)
    for agent in model.agents:
        if hasattr(agent, "domain_agent"):
            assert agent.domain_agent.collateral_posted == 0.0


def test_flop_threshold_signal_scales_with_excess():
    """Test that FLOP-based signal strength scales with FLOP excess.

    When flop_threshold > 0, signal generation uses planned_training_flops
    instead of capacity. Larger training runs produce stronger signals.
    """
    from compute_permit_sim.core.enforcement import Auditor

    audit_config = AuditConfig(
        base_prob=0.05,
        high_prob=0.5,
        false_positive_rate=0.0,
        false_negative_rate=0.0,
        penalty_amount=1.0,
        backcheck_prob=0.0,
    )
    auditor = Auditor(audit_config)
    flop_threshold = 1e25

    # Below threshold: minimal signal
    signal_below = auditor.compute_signal_strength(
        used_compute=5e24, flop_threshold=flop_threshold, is_compliant=False
    )
    assert signal_below == 0.1  # below threshold

    # At 1.5x threshold: moderate signal
    signal_mid = auditor.compute_signal_strength(
        used_compute=1.5e25, flop_threshold=flop_threshold, is_compliant=False
    )
    assert 0.5 < signal_mid < 1.0

    # At 2x threshold: maximum signal
    signal_max = auditor.compute_signal_strength(
        used_compute=2e25, flop_threshold=flop_threshold, is_compliant=False
    )
    assert signal_max == 1.0

    # Ordering: below < mid < max
    assert signal_below < signal_mid < signal_max


def test_flop_threshold_below_threshold_low_signal():
    """Test that labs below the FLOP threshold generate minimal signal."""
    from compute_permit_sim.core.enforcement import Auditor

    audit_config = AuditConfig(
        base_prob=0.05,
        high_prob=0.5,
        false_positive_rate=0.0,
        false_negative_rate=0.0,
        penalty_amount=1.0,
        backcheck_prob=0.0,
    )
    auditor = Auditor(audit_config)
    # Lab's training FLOPs below threshold → minimal signal
    signal = auditor.compute_signal_strength(
        used_compute=5e24, flop_threshold=1e25, is_compliant=False
    )
    assert signal == 0.1  # below threshold = minimal


def test_flop_threshold_integration():
    """Test full simulation with FLOP-based threshold enabled."""
    audit, market, lab = get_base_configs()
    audit = audit.model_copy(
        update={"penalty_amount": 100.0, "base_prob": 0.5, "high_prob": 0.9}
    )
    # Set training FLOP range — all labs above threshold → need permits
    lab = lab.model_copy(
        update={"training_flops_min": 2e25, "training_flops_max": 5e25}
    )
    config = ScenarioConfig(
        name="Test FLOP Integration",
        n_agents=10,
        steps=3,
        audit=audit,
        market=market,
        lab=lab,
        seed=42,
        flop_threshold=1e25,  # All labs exceed this
    )
    model = ComputePermitModel(config)
    for _ in range(3):
        model.step()
    df = model.datacollector.get_model_vars_dataframe()
    assert len(df) == 3
    # High penalty + high audit → high compliance
    assert df["Compliance_Rate"].iloc[-1] == 1.0


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
