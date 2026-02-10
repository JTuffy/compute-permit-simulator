"""Basic tests for domain model and agent initialization."""

import pytest

from compute_permit_sim.core.agents import Lab
from compute_permit_sim.core.enforcement import Auditor
from compute_permit_sim.core.market import SimpleClearingMarket
from compute_permit_sim.schemas import AuditConfig, LabConfig


def test_lab_initialization() -> None:
    """Verify that a Lab agent correctly initializes with provided values and defaults."""
    lab_config = LabConfig()
    lab = Lab(
        lab_id=1, config=lab_config, economic_value=1.5, risk_profile=1.0, capacity=2.0
    )
    assert lab.lab_id == 1
    assert lab.economic_value == 1.5
    assert lab.is_compliant is True
    assert lab.has_permit is False
    assert lab.get_bid() == 1.5


def test_auditor_initialization() -> None:
    """Verify that the Auditor correctly initializes and computes effective detection probability."""
    config = AuditConfig(
        base_prob=0.1,
        high_prob=0.5,
        false_positive_rate=0.05,
        false_negative_rate=0.1,
        penalty_amount=0.8,
        backcheck_prob=0.2,
    )
    auditor = Auditor(config)
    # Check effective detection with signal_strength=1.0 (default, max suspicion)
    # New formula:
    #   p_audit = base_prob + signal_strength * (high_prob - base_prob)
    #           = 0.1 + 1.0 * (0.5 - 0.1) = 0.5
    #   p_catch_if_audited = 1 - false_negative_rate = 0.9
    #   p_catch = p_audit * p_catch_if_audited = 0.5 * 0.9 = 0.45
    #   p_eff = p_catch + (1 - p_catch) * backcheck_prob
    #         = 0.45 + 0.55 * 0.2 = 0.56
    p_eff = auditor.compute_effective_detection()
    assert p_eff == pytest.approx(0.56)


def test_penalty_flat_default() -> None:
    """When flexible penalty is not configured, penalty_amount is used."""
    config = AuditConfig(base_prob=0.1, high_prob=0.5, penalty_amount=100.0)
    auditor = Auditor(config)
    # With firm_value but no flexible config (penalty_fixed=0, penalty_percentage=0)
    assert auditor.compute_penalty_amount(firm_value=5000.0) == 100.0
    # Without firm_value
    assert auditor.compute_penalty_amount(firm_value=None) == 100.0


def test_penalty_flexible_fixed_floor() -> None:
    """Flexible penalty uses fixed floor when it exceeds percentage."""
    config = AuditConfig(
        base_prob=0.1,
        high_prob=0.5,
        penalty_amount=50.0,  # legacy fallback (should not be used)
        penalty_fixed=200.0,  # fixed floor
        penalty_percentage=0.07,  # 7% of revenue
    )
    auditor = Auditor(config)
    # Small firm: 7% of 1000 = 70 < 200 fixed → use fixed
    assert auditor.compute_penalty_amount(firm_value=1000.0) == 200.0


def test_penalty_flexible_percentage_dominates() -> None:
    """Flexible penalty uses percentage when it exceeds fixed floor."""
    config = AuditConfig(
        base_prob=0.1,
        high_prob=0.5,
        penalty_fixed=200.0,
        penalty_percentage=0.07,
    )
    auditor = Auditor(config)
    # Large firm: 7% of 5000 = 350 > 200 fixed → use percentage
    assert auditor.compute_penalty_amount(firm_value=5000.0) == pytest.approx(350.0)


def test_penalty_ceiling_caps() -> None:
    """Penalty ceiling limits the maximum penalty."""
    config = AuditConfig(
        base_prob=0.1,
        high_prob=0.5,
        penalty_fixed=200.0,
        penalty_percentage=0.07,
        penalty_ceiling=300.0,
    )
    auditor = Auditor(config)
    # 7% of 5000 = 350, but ceiling is 300 → capped at 300
    assert auditor.compute_penalty_amount(firm_value=5000.0) == 300.0
    # 7% of 1000 = 70 < 200 fixed, and 200 < 300 ceiling → 200
    assert auditor.compute_penalty_amount(firm_value=1000.0) == 200.0


def test_penalty_ceiling_on_flat() -> None:
    """Penalty ceiling also applies to flat penalty_amount fallback."""
    config = AuditConfig(
        base_prob=0.1,
        high_prob=0.5,
        penalty_amount=500.0,
        penalty_ceiling=300.0,
    )
    auditor = Auditor(config)
    # Flat penalty 500 capped by ceiling 300
    assert auditor.compute_penalty_amount(firm_value=1000.0) == 300.0


def test_apply_penalty_no_violation() -> None:
    """apply_penalty returns 0 when no violation found."""
    config = AuditConfig(base_prob=0.1, high_prob=0.5, penalty_amount=100.0)
    auditor = Auditor(config)
    assert auditor.apply_penalty(violation_found=False, firm_value=5000.0) == 0.0


def test_reputation_sensitivity_escalation() -> None:
    """Test that failed audits increase reputation sensitivity via escalation factor."""
    lab_config = LabConfig(reputation_escalation_factor=0.5)
    lab = Lab(
        lab_id=1,
        config=lab_config,
        economic_value=100.0,
        risk_profile=1.0,
        capacity=2.0,
    )

    base = lab.reputation_sensitivity
    assert lab.current_reputation_sensitivity == base

    # First failure: rep_sens = base × (1 + 0.5)^1 = base × 1.5
    lab.on_audit_failure(audit_escalation=0.0)
    assert lab.current_reputation_sensitivity == pytest.approx(base * 1.5)
    assert lab.failed_audit_count == 1

    # Second failure: rep_sens = base × (1 + 0.5)^2 = base × 2.25
    lab.on_audit_failure(audit_escalation=0.0)
    assert lab.current_reputation_sensitivity == pytest.approx(base * 2.25)
    assert lab.failed_audit_count == 2


def test_reputation_sensitivity_static_when_zero() -> None:
    """Test that reputation sensitivity stays static when escalation_factor=0."""
    lab_config = LabConfig(reputation_escalation_factor=0.0)
    lab = Lab(
        lab_id=1,
        config=lab_config,
        economic_value=100.0,
        risk_profile=1.0,
        capacity=2.0,
    )
    base = lab.current_reputation_sensitivity

    lab.on_audit_failure()
    assert lab.current_reputation_sensitivity == base  # unchanged


def test_audit_coefficient_escalation_and_decay() -> None:
    """Test audit coefficient escalates on failure and decays over time."""
    lab_config = LabConfig()
    lab = Lab(
        lab_id=1,
        config=lab_config,
        economic_value=100.0,
        risk_profile=1.0,
        capacity=2.0,
    )
    base_coeff = lab.audit_coefficient

    # Escalate by 1.0
    lab.on_audit_failure(audit_escalation=1.0)
    assert lab.current_audit_coefficient == base_coeff + 1.0

    # Decay with rate 0.5: excess = 1.0, new_excess = 0.5
    lab.decay_audit_coefficient(decay_rate=0.5)
    assert lab.current_audit_coefficient == pytest.approx(base_coeff + 0.5)

    # Decay again: excess = 0.5, new_excess = 0.25
    lab.decay_audit_coefficient(decay_rate=0.5)
    assert lab.current_audit_coefficient == pytest.approx(base_coeff + 0.25)


def test_audit_coefficient_no_decay_below_base() -> None:
    """Test that decay doesn't push coefficient below base value."""
    lab_config = LabConfig()
    lab = Lab(
        lab_id=1,
        config=lab_config,
        economic_value=100.0,
        risk_profile=1.0,
        capacity=2.0,
    )
    # Coefficient at base — decay should do nothing
    lab.decay_audit_coefficient(decay_rate=0.8)
    assert lab.current_audit_coefficient == lab.audit_coefficient


def test_racing_factor_update() -> None:
    """Test racing factor updates based on capability gap."""
    lab_config = LabConfig(racing_gap_sensitivity=0.5, capability_scale=10.0)
    lab = Lab(
        lab_id=1,
        config=lab_config,
        economic_value=100.0,
        risk_profile=1.0,
        capacity=2.0,
    )
    base_racing = lab.base_racing_factor

    # Lab has more capability than average → racing factor increases
    lab.cumulative_capability = 15.0
    lab.update_racing_factor(mean_capability=10.0)
    # gap = 5, multiplier = 1 + 0.5 * 5 / 10 = 1.25
    assert lab.racing_factor == pytest.approx(base_racing * 1.25)

    # Lab has less capability → racing factor decreases
    lab.cumulative_capability = 5.0
    lab.update_racing_factor(mean_capability=10.0)
    # gap = -5, multiplier = 1 + 0.5 * (-5) / 10 = 0.75
    assert lab.racing_factor == pytest.approx(base_racing * 0.75)


def test_racing_factor_static_when_zero() -> None:
    """Test racing factor stays static when gap_sensitivity=0."""
    lab_config = LabConfig(racing_gap_sensitivity=0.0)
    lab = Lab(
        lab_id=1,
        config=lab_config,
        economic_value=100.0,
        risk_profile=1.0,
        capacity=2.0,
    )
    original = lab.racing_factor

    lab.cumulative_capability = 100.0
    lab.update_racing_factor(mean_capability=0.0)
    assert lab.racing_factor == original  # unchanged


def test_market_initialization() -> None:
    """Verify that the SimpleClearingMarket initializes with correct supply and default price."""
    market = SimpleClearingMarket(token_cap=10)
    assert market.max_supply == 10
    assert market.current_price == 0.0
    assert market.fixed_price is None
