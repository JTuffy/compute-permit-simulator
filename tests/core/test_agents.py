"""Tests for Lab agent behavior and initialization."""

import pytest

from compute_permit_sim.core.agents import Lab
from compute_permit_sim.schemas import LabConfig


def test_lab_initialization() -> None:
    """Verify that a Lab agent correctly initializes with provided values and defaults."""
    lab_config = LabConfig()
    lab = Lab(
        lab_id=1,
        config=lab_config,
        economic_value=1.5,
        risk_profile=1.0,
        planned_training_flops=1e25,
    )
    assert lab.lab_id == 1
    assert lab.economic_value == 1.5
    assert lab.is_compliant is True
    assert lab.has_permit is False
    assert lab.get_bid() == 1.5


def test_reputation_sensitivity_escalation() -> None:
    """Test that failed audits increase reputation sensitivity via escalation factor."""
    lab_config = LabConfig(reputation_escalation_factor=0.5)
    lab = Lab(
        lab_id=1,
        config=lab_config,
        economic_value=100.0,
        risk_profile=1.0,
        planned_training_flops=1e25,
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
        planned_training_flops=1e25,
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
        planned_training_flops=1e25,
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
        planned_training_flops=1e25,
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
        planned_training_flops=1e25,
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
        planned_training_flops=1e25,
    )
    original = lab.racing_factor

    lab.cumulative_capability = 100.0
    lab.update_racing_factor(mean_capability=0.0)
    assert lab.racing_factor == original  # unchanged
