"""Tests for Auditor behavior and penalty calculations."""

import pytest

from compute_permit_sim.core.enforcement import Auditor
from compute_permit_sim.schemas import AuditConfig


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
