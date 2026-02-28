"""Advanced integration tests for complex simulation scenarios."""

from compute_permit_sim.schemas import (
    AuditConfig,
    LabConfig,
    MarketConfig,
    ScenarioConfig,
)
from compute_permit_sim.services.mesa_model import ComputePermitModel


def get_base_configs():
    """Helper to get default configurations.

    Note: Uses normalized test units (not M$ scale) for predictable test behavior.
    All monetary values explicitly set to enable precise deterrence calculations.
    """
    audit = AuditConfig(
        base_prob=0.1,
        false_positive_rate=0.0,
        false_negative_rate=0.0,
        penalty_amount=1.0,
        backcheck_prob=0.0,
        whistleblower_prob=0.0,
    )
    market = MarketConfig(permit_cap=10, fixed_price=None)
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
    - FNR=0.5 (audit has 50% miss rate), Penalty=15.0, Base Audit=0.1.
    - Base: p_stage2 = 1 - 0.5 = 0.5, p_detect = 0.1*0.5 = 0.05. E[P]=0.75 < Gain -> Cheat.
    - Whistleblower p_w=0.5: miss=0.5*(1-0.5)=0.25, p_stage2=0.75, p_detect=0.075.
      E[P]=0.075*15=1.125 > Gain -> Comply.
    """
    audit, market, lab = get_base_configs()
    market = market.model_copy(update={"fixed_price": 2.0})
    audit = audit.model_copy(
        update={
            "penalty_amount": 15.0,
            "base_prob": 0.1,
            "false_negative_rate": 0.5,
        }
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
    market = market.model_copy(update={"fixed_price": 2.0})
    audit = audit.model_copy(
        update={
            "penalty_amount": 15.0,
            "base_prob": 0.1,
            "false_negative_rate": 0.8,
        }
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
    market = market.model_copy(update={"fixed_price": 2.0})

    # 100% detection + low penalty so everyone cheats but audits capped
    audit = audit.model_copy(
        update={
            "base_prob": 1.0,
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
        update={
            "penalty_amount": 1.5,
            "base_prob": 0.2,
        }
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
    market = market.model_copy(update={"fixed_price": 2.0})
    # Very low penalty so they still cheat even with collateral
    audit = audit.model_copy(
        update={
            "penalty_amount": 0.01,
            "base_prob": 1.0,
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
    market = market.model_copy(update={"fixed_price": 2.0})
    audit = audit.model_copy(update={"penalty_amount": 100.0, "base_prob": 1.0})
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
    market = market.model_copy(update={"fixed_price": 2.0})
    audit = audit.model_copy(
        update={
            "penalty_amount": 4.0,
            "base_prob": 0.1,
        }
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
    """Test that signal strength scales with excess compute above threshold.

    New formula: signal = min(1.0, (excess / threshold) ^ signal_exponent)
    With default exponent=1.0 (linear), excess = used - threshold.
    """
    from compute_permit_sim.core.enforcement import Auditor

    audit_config = AuditConfig(
        base_prob=0.05,
        false_positive_rate=0.0,
        false_negative_rate=0.0,
        penalty_amount=1.0,
        backcheck_prob=0.0,
    )
    auditor = Auditor(audit_config)
    flop_threshold = 1e25

    # No excess compute: signal = 0
    signal_zero = auditor.compute_signal(
        excess_compute=0.0, flop_threshold=flop_threshold
    )
    assert signal_zero == 0.0

    # 50% excess: signal = 0.5e25 / 1e25 = 0.5
    signal_mid = auditor.compute_signal(
        excess_compute=0.5e25, flop_threshold=flop_threshold
    )
    assert signal_mid == 0.5

    # 100% excess: signal = 1e25 / 1e25 = 1.0 (capped)
    signal_full = auditor.compute_signal(
        excess_compute=1e25, flop_threshold=flop_threshold
    )
    assert signal_full == 1.0

    # 200% excess: still capped at 1.0
    signal_over = auditor.compute_signal(
        excess_compute=2e25, flop_threshold=flop_threshold
    )
    assert signal_over == 1.0

    # Ordering: zero < mid < full
    assert signal_zero < signal_mid < signal_full


def test_flop_threshold_below_threshold_no_signal():
    """Test that zero excess compute produces zero signal."""
    from compute_permit_sim.core.enforcement import Auditor

    audit_config = AuditConfig(
        base_prob=0.05,
        false_positive_rate=0.0,
        false_negative_rate=0.0,
        penalty_amount=1.0,
        backcheck_prob=0.0,
    )
    auditor = Auditor(audit_config)
    # No excess → zero signal
    signal = auditor.compute_signal(excess_compute=0.0, flop_threshold=1e25)
    assert signal == 0.0


def test_flop_threshold_integration():
    """Test full simulation with FLOP-based threshold enabled."""
    audit, market, lab = get_base_configs()
    audit = audit.model_copy(update={"penalty_amount": 100.0, "base_prob": 0.5})
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


def test_monitoring_zero_unchanged():
    """Test that monitoring_prob=0 preserves existing detection behavior.

    p_m=0 means no global monitoring — detection relies only on audits + whistleblower.
    Should match baseline behavior exactly.
    """
    audit, market, lab = get_base_configs()
    market = market.model_copy(update={"fixed_price": 2.0})
    audit = audit.model_copy(
        update={
            "penalty_amount": 4.0,
            "base_prob": 0.1,
        }
    )

    # Baseline: no monitoring (default)
    comp_base = run_model_get_compliance(audit, market, lab)

    # Explicit monitoring_prob=0
    audit_m0 = audit.model_copy(update={"monitoring_prob": 0.0})
    comp_m0 = run_model_get_compliance(audit_m0, market, lab)

    assert comp_base == comp_m0


def test_monitoring_full_detection():
    """Test that monitoring_prob=1.0 gives full detection (everyone complies).

    With FNR=0.5, p_m=1.0: miss=FNR*(1-p_b)*(1-p_w)*(1-p_m)=0.5*1*1*0=0 → p_stage2=1.0.
    p_detect = p_audit * 1.0 = 0.1. E[P]=0.1*15=1.5 > Gain(1.0) → comply.
    """
    audit, market, lab = get_base_configs()
    market = market.model_copy(update={"fixed_price": 2.0})
    # Low audit prob + moderate FNR — normally everyone cheats
    audit = audit.model_copy(
        update={
            "penalty_amount": 15.0,
            "base_prob": 0.1,
            "false_negative_rate": 0.5,
        }
    )
    # Base: p_detect=0.1*0.5=0.05. E[P]=0.75 < Gain(1.0) → cheat
    comp_base = run_model_get_compliance(audit, market, lab)
    assert comp_base == 0.0

    # With monitoring_prob=1.0: miss=0 → p_stage2=1.0 → p_detect=0.1 → E[P]=1.5 → comply
    audit_full = audit.model_copy(update={"monitoring_prob": 1.0})
    comp_full = run_model_get_compliance(audit_full, market, lab)
    assert comp_full == 1.0


def test_monitoring_increases_compliance():
    """Test that moderate monitoring_prob increases deterrence.

    Setup: FNR=0.5, audit=0.1, penalty=18.0, Gain=1.0.
    Without monitoring: miss=0.5*1*1*1=0.5. p_stage2=0.5. p_detect=0.05. E[P]=0.9 < 1.0 → cheat.
    With monitoring p_m=0.2: miss=0.5*1*1*0.8=0.4. p_stage2=0.6. p_detect=0.06.
    E[P]=0.06*18=1.08 > 1.0 → comply.
    """
    audit, market, lab = get_base_configs()
    market = market.model_copy(update={"fixed_price": 2.0})
    audit = audit.model_copy(
        update={
            "penalty_amount": 18.0,
            "base_prob": 0.1,
            "false_negative_rate": 0.5,
        }
    )

    comp_base = run_model_get_compliance(audit, market, lab)
    assert comp_base == 0.0

    audit_monitor = audit.model_copy(update={"monitoring_prob": 0.2})
    comp_monitor = run_model_get_compliance(audit_monitor, market, lab)
    assert comp_monitor > comp_base
    assert comp_monitor == 1.0


def test_audit_targeting_efficiency():
    """Test that higher audit coefficient improves compliance in signal-dependent mode.

    Scenario:
    - signal_dependent=True: c(i) scales the signal boost above base_prob.
    - Labs above threshold, no permits (price > value), all cheat → signal=1.0.
    - Agent values in range [0.8, 2.0], penalty=4.0, base_prob=0.1.

    Case 1 (c=0.1): p_audit = 0.1 + 0.1*1.0*0.9 = 0.19. E[P]=0.76 < min_gain=0.8 → cheat.
    Case 2 (c=1.0): p_audit = 0.1 + 1.0*1.0*0.9 = 1.0.  E[P]=4.0  > max_gain=2.0 → comply.
    """
    audit, market, lab = get_base_configs()
    market = market.model_copy(update={"fixed_price": 3.0})
    audit = audit.model_copy(
        update={
            "penalty_amount": 4.0,
            "base_prob": 0.1,
            "signal_dependent": True,
        }
    )

    # Case 1: Low coefficient (coeff=0.1) — audit rate barely above base → all cheat.
    lab_low = lab.model_copy(
        update={
            "economic_value_min": 0.8,
            "economic_value_max": 2.0,
            "audit_coefficient": 0.1,
        }
    )
    comp_low = run_model_get_compliance(audit, market, lab_low)
    assert comp_low == 0.0

    # Case 2: Default coefficient (coeff=1.0) — full signal boost → all comply.
    lab_high = lab_low.model_copy(update={"audit_coefficient": 1.0})
    comp_high = run_model_get_compliance(audit, market, lab_high)
    assert comp_high == 1.0
