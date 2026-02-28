"""Tests for Auditor behavior and enforcement logic."""

import pytest

from compute_permit_sim.core.enforcement import Auditor
from compute_permit_sim.schemas import AuditConfig

# ---------------------------------------------------------------------------
# Stage 1: Signal computation
# ---------------------------------------------------------------------------


def test_compute_signal() -> None:
    auditor = Auditor(AuditConfig())
    assert auditor.compute_signal(0.0, flop_threshold=1e25) == 0.0
    assert auditor.compute_signal(0.5e25, flop_threshold=1e25) == pytest.approx(0.5)
    assert auditor.compute_signal(1e25, flop_threshold=1e25) == pytest.approx(1.0)
    # excess > threshold → capped at 1.0
    assert auditor.compute_signal(2e25, flop_threshold=1e25) == pytest.approx(1.0)


def test_compute_signal_quadratic_exponent() -> None:
    auditor = Auditor(AuditConfig(signal_exponent=2.0))
    # excess = 0.5 × threshold, quadratic → signal = 0.5² = 0.25
    assert auditor.compute_signal(0.5e25, flop_threshold=1e25) == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# Stage 1: Audit occurrence probability
# ---------------------------------------------------------------------------


def test_compute_audit_probability_random_mode() -> None:
    # Default: signal_dependent=False → pure random, signal is irrelevant
    auditor = Auditor(AuditConfig())
    assert auditor.compute_audit_probability(signal=1.0) == pytest.approx(0.05)
    assert auditor.compute_audit_probability(signal=0.0) == pytest.approx(0.05)


def test_compute_audit_probability_signal_dependent() -> None:
    auditor = Auditor(AuditConfig(signal_dependent=True))
    # p_audit = base_prob + signal × (1 - base_prob)
    # signal=1.0: 0.05 + 0.95 = 1.0
    assert auditor.compute_audit_probability(signal=1.0) == pytest.approx(1.0)
    # signal=0.0: 0.05 + 0.0 = 0.05
    assert auditor.compute_audit_probability(signal=0.0) == pytest.approx(0.05)


def test_compute_audit_probability_coefficient() -> None:
    # c(i) only scales the signal component in signal-dependent mode
    auditor = Auditor(AuditConfig(signal_dependent=True))
    # base=0.05, signal=0.5, c(i)=2.0: 0.05 + 2.0*0.5*0.95 = 1.0
    assert auditor.compute_audit_probability(
        signal=0.5, audit_coefficient=2.0
    ) == pytest.approx(1.0)
    # base=0.05, signal=0.5, c(i)=0.5: 0.05 + 0.5*0.5*0.95 = 0.2875
    assert auditor.compute_audit_probability(
        signal=0.5, audit_coefficient=0.5
    ) == pytest.approx(0.2875)
    # large coefficient still capped at 1.0
    assert auditor.compute_audit_probability(
        signal=1.0, audit_coefficient=100.0
    ) == pytest.approx(1.0)


def test_compute_audit_probability_floor() -> None:
    # In random mode, c(i) has no effect — everyone gets exactly base_prob
    auditor = Auditor(AuditConfig())
    assert auditor.compute_audit_probability(
        signal=0.0, audit_coefficient=0.5
    ) == pytest.approx(0.05)
    assert auditor.compute_audit_probability(
        signal=0.0, audit_coefficient=2.0
    ) == pytest.approx(0.05)
    assert auditor.compute_audit_probability(
        signal=1.0, audit_coefficient=2.0
    ) == pytest.approx(0.05)
    # In signal mode, base_prob is always present regardless of c(i) or signal
    auditor_sd = Auditor(AuditConfig(signal_dependent=True))
    # c(i)=0.0: p_audit = 0.05 + 0.0*signal*0.95 = 0.05 (just base_prob)
    assert auditor_sd.compute_audit_probability(
        signal=1.0, audit_coefficient=0.0
    ) == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Stage 2: Catch probability (analytical)
# ---------------------------------------------------------------------------


def test_compute_catch_probability() -> None:
    auditor = Auditor(AuditConfig())
    # FNR=0.40, backcheck=0.0, p_w=0, p_m=0
    # miss = 0.40 * 1.0 * 1.0 * 1.0 = 0.40 → catch = 0.60
    assert auditor.compute_catch_probability() == pytest.approx(0.60)
    # p_w=0.5, p_m=0.2: miss = 0.40 * 1.0 * 0.5 * 0.8 = 0.16 → catch = 0.84
    assert auditor.compute_catch_probability(p_w=0.5, p_m=0.2) == pytest.approx(0.84)


def test_compute_catch_probability_zero_fnr() -> None:
    auditor = Auditor(AuditConfig(false_negative_rate=0.0))
    assert auditor.compute_catch_probability() == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Stage 2: audit_detection_channel (deterministic via extreme values)
# ---------------------------------------------------------------------------


def test_audit_detection_channel_compliant_no_fp_no_backcheck() -> None:
    # FPR=0.0, backcheck=0.0 → never caught
    auditor = Auditor(AuditConfig(false_positive_rate=0.0, backcheck_prob=0.0))
    caught, caught_backcheck = auditor.audit_detection_channel(is_compliant=True)
    assert caught is False
    assert caught_backcheck is False


def test_audit_detection_channel_compliant_direct_fp() -> None:
    # FPR=1.0, backcheck=0.0 → always caught on direct; backcheck not reached
    auditor = Auditor(AuditConfig(false_positive_rate=1.0, backcheck_prob=0.0))
    caught, caught_backcheck = auditor.audit_detection_channel(is_compliant=True)
    assert caught is True
    assert caught_backcheck is False


def test_audit_detection_channel_compliant_backcheck_fp() -> None:
    # FPR=0.0 (direct never fires) + backcheck=1.0 → always caught via backcheck
    auditor = Auditor(
        AuditConfig(
            false_positive_rate=0.0,
            backcheck_prob=1.0,
            whistleblower_prob=0.0,
            monitoring_prob=0.0,
        )
    )
    caught, caught_backcheck = auditor.audit_detection_channel(is_compliant=True)
    assert caught is True
    assert caught_backcheck is True


def test_audit_detection_channel_non_compliant_direct_catch() -> None:
    # FNR=0.0 → direct pass always fires
    auditor = Auditor(AuditConfig(false_negative_rate=0.0))
    caught, caught_backcheck = auditor.audit_detection_channel(is_compliant=False)
    assert caught is True
    assert caught_backcheck is False


def test_audit_detection_channel_non_compliant_guaranteed_miss() -> None:
    # FNR=1.0 + backcheck=0.0 + no monitoring → always misses
    auditor = Auditor(
        AuditConfig(
            false_negative_rate=1.0,
            backcheck_prob=0.0,
            whistleblower_prob=0.0,
            monitoring_prob=0.0,
        )
    )
    caught, caught_backcheck = auditor.audit_detection_channel(
        is_compliant=False, p_w=0.0, p_m=0.0
    )
    assert caught is False
    assert caught_backcheck is False


def test_audit_detection_channel_caught_via_backcheck() -> None:
    # FNR=1.0 (always misses direct) + backcheck=1.0 (always fires on review)
    auditor = Auditor(
        AuditConfig(
            false_negative_rate=1.0,
            backcheck_prob=1.0,
            whistleblower_prob=0.0,
            monitoring_prob=0.0,
        )
    )
    caught, caught_backcheck = auditor.audit_detection_channel(is_compliant=False)
    assert caught is True
    assert caught_backcheck is True


def test_audit_detection_channel_caught_via_monitoring() -> None:
    # FNR=1.0, backcheck=0.0 → only p_m can catch
    auditor = Auditor(
        AuditConfig(
            false_negative_rate=1.0,
            backcheck_prob=0.0,
            whistleblower_prob=0.0,
            monitoring_prob=0.0,
        )
    )
    caught, caught_backcheck = auditor.audit_detection_channel(
        is_compliant=False, p_m=1.0
    )
    assert caught is True
    assert caught_backcheck is False


def test_audit_detection_channel_returns_two_bools() -> None:
    auditor = Auditor(AuditConfig(false_negative_rate=0.0))
    result = auditor.audit_detection_channel(is_compliant=False)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(v, bool) for v in result)


# ---------------------------------------------------------------------------
# audit_finds_violation wrapper
# ---------------------------------------------------------------------------


def test_audit_finds_violation() -> None:
    assert (
        Auditor(AuditConfig(false_negative_rate=0.0)).audit_finds_violation(
            is_compliant=False
        )
        is True
    )
    assert (
        Auditor(
            AuditConfig(false_positive_rate=0.0, backcheck_prob=0.0)
        ).audit_finds_violation(is_compliant=True)
        is False
    )


# ---------------------------------------------------------------------------
# Combined detection probability
# ---------------------------------------------------------------------------


def test_compute_detection_probability() -> None:
    auditor = Auditor(AuditConfig())
    # signal_dependent=False, base_prob=0.05, FNR=0.40, backcheck=0.0
    # p_audit=0.05, p_stage2 = 1 - 0.4*1*1*1 = 0.60
    # p_detect = 0.05 * 0.60 = 0.03
    p = auditor.compute_detection_probability(excess_compute=1e25, flop_threshold=1e25)
    assert p == pytest.approx(0.03)

    # p_w=0.5, p_m=0.2: miss = 0.4 * 1.0 * 0.5 * 0.8 = 0.16 → p_stage2 = 0.84
    # p_detect = 0.05 * 0.84 = 0.042
    p = auditor.compute_detection_probability(
        excess_compute=1e25, flop_threshold=1e25, p_w=0.5, p_m=0.2
    )
    assert p == pytest.approx(0.042)


# ---------------------------------------------------------------------------
# Penalty
# ---------------------------------------------------------------------------


def test_apply_penalty() -> None:
    auditor = Auditor(AuditConfig())
    assert auditor.apply_penalty(violation_found=False, penalty_amount=200.0) == 0.0
    assert auditor.apply_penalty(
        violation_found=True, penalty_amount=200.0
    ) == pytest.approx(200.0)
