"""Enforcement logic for the Auditor.

Implements a two-stage audit model:

1. SIGNAL GENERATION & AUDIT OCCURRENCE:
   - Auditor observes signals from firms based on their compute usage
   - Non-compliant firms generate stronger signals based on compute excess
   - Audit probability depends on signal strength (pi_0 baseline, pi_1 suspicious)

2. AUDIT OUTCOME:
   - If audit occurs, FPR/FNR determine whether violation is detected
   - false_positive_rate (alpha): P(false alarm | compliant firm audited)
   - false_negative_rate (beta): P(miss | non-compliant firm audited)

Effective detection probability:
    p_audit = base_prob + signal_strength * (high_prob - base_prob)
    p_catch = p_audit * (1 - false_negative_rate)
    p_eff = p_catch + (1 - p_catch) * backcheck_prob
"""

import random

from compute_permit_sim.schemas import AuditConfig


class Auditor:
    """The Auditor agent handling audits and enforcement.

    Attributes:
        config: Audit policy configuration.
        _rng: Random number generator for reproducibility.
    """

    def __init__(self, config: AuditConfig, rng: random.Random | None = None) -> None:
        """Initialize the Auditor.

        Args:
            config: Audit configuration parameters.
            rng: Optional seeded Random instance for reproducibility.
                 If None, uses the global random module.
        """
        self.config = config
        self._rng = rng

    def _random(self) -> float:
        """Get a random float using the configured RNG or global random."""
        if self._rng is not None:
            return self._rng.random()
        return random.random()

    def compute_signal_strength(
        self,
        used_compute: float,
        flop_threshold: float,
        is_compliant: bool,
    ) -> float:
        """Compute signal strength based on compute usage relative to threshold.

        For non-compliant firms, signal strength increases with compute excess.
        Compliant firms have zero signal (no suspicious activity).

        Args:
            used_compute: Actual compute used by the firm.
            flop_threshold: Regulatory threshold requiring permits.
            is_compliant: Whether the firm is compliant.

        Returns:
            Signal strength in [0, 1]. Higher = more suspicious.
        """
        if is_compliant:
            # Compliant firms: no suspicious signal
            return 0.0

        # Non-compliant firms: signal scales with compute excess above threshold
        if flop_threshold <= 0:
            # No threshold means any unpermitted compute is visible
            return 1.0 if used_compute > 0 else 0.0

        if used_compute <= flop_threshold:
            # Below threshold: minimal signal (borderline case)
            return 0.1

        # Signal strength based on how far above threshold
        # At threshold: signal ~= 0.5 (borderline suspicious)
        # At 2x threshold: signal = 1.0 (very suspicious)
        # This models: larger training runs are harder to hide
        excess_ratio = (used_compute - flop_threshold) / flop_threshold
        signal = 0.5 + 0.5 * min(1.0, excess_ratio)
        return signal

    def compute_effective_detection(
        self,
        audit_coefficient: float = 1.0,
        signal_strength: float = 1.0,
    ) -> float:
        """Compute the effective detection probability for a firm.

        This accounts for:
        - Probability of audit occurring (based on signal strength)
        - Probability of audit success (based on FNR)
        - Backcheck probability (historical discovery)

        Args:
            audit_coefficient: Firm-specific scaling factor c(i) for audit rate.
            signal_strength: How detectable the violation is (0-1).

        Returns:
            The effective detection probability p_eff in [0, 1].
        """
        # Probability of audit occurring (interpolate between base and high prob)
        p_audit = self.config.base_prob + signal_strength * (
            self.config.high_prob - self.config.base_prob
        )
        p_audit = min(1.0, p_audit * audit_coefficient)

        # Probability of catching violation if audited (1 - FNR)
        p_catch_if_audited = 1.0 - self.config.false_negative_rate

        # Combined probability: audit occurs AND catches violation
        p_catch = p_audit * p_catch_if_audited

        # Add backcheck probability for historical discovery
        p_eff = p_catch + (1.0 - p_catch) * self.config.backcheck_prob
        return p_eff

    def generate_signal(
        self,
        used_compute: float,
        flop_threshold: float,
        is_compliant: bool,
    ) -> float:
        """Generate a suspicion signal based on compute usage.

        Args:
            used_compute: Actual compute used by the firm.
            flop_threshold: Regulatory threshold requiring permits.
            is_compliant: Whether the firm is compliant.

        Returns:
            Signal strength in [0, 1]. Used to determine audit probability.
        """
        return self.compute_signal_strength(used_compute, flop_threshold, is_compliant)

    def decide_audit(self, signal_strength: float) -> bool:
        """Decide whether to audit based on signal strength.

        Policy:
            - All firms face base_prob (pi_0) chance of random audit
            - Additional probability from signal: interpolate to high_prob (pi_1)
            - Final audit_prob = base_prob + signal_strength * (high_prob - base_prob)

        Args:
            signal_strength: Suspicion level from 0 (clean) to 1 (very suspicious).

        Returns:
            True if an audit is triggered.
        """
        audit_prob = self.config.base_prob + signal_strength * (
            self.config.high_prob - self.config.base_prob
        )
        return self._random() < audit_prob

    def audit_finds_violation(self, is_compliant: bool) -> bool:
        """Determine if an audit discovers a violation.

        Uses FPR/FNR to model audit accuracy:
        - Compliant firm: false_positive_rate chance of wrongly flagging
        - Non-compliant firm: (1 - false_negative_rate) chance of catching

        Args:
            is_compliant: True if the firm is actually compliant.

        Returns:
            True if the audit finds (or falsely reports) a violation.
        """
        if is_compliant:
            # False positive: wrongly finding a violation
            return self._random() < self.config.false_positive_rate
        else:
            # True positive: correctly finding a violation
            # P(catch) = 1 - P(miss) = 1 - false_negative_rate
            return self._random() < (1.0 - self.config.false_negative_rate)

    def compute_penalty_amount(self, firm_value: float | None = None) -> float:
        """Compute the penalty for a given firm.

        Two modes:
        1. Flexible (opt-in): max(penalty_fixed, penalty_percentage × firm_revenue)
           Activated when penalty_fixed > 0 or penalty_percentage > 0.
           Optionally capped by penalty_ceiling.
        2. Flat (default): penalty_amount — used when flexible system is off
           or firm_value is not provided.

        Reference: Christoph (2026) Section 2.5 — effective punishment
        P = min(K + phi, L) where L is the limited liability bound.
        Here penalty_ceiling plays the role of L (limited liability).

        Args:
            firm_value: The firm's annual revenue (M$) for flexible penalty.
                If None, uses flat penalty_amount.

        Returns:
            The computed penalty amount (M$).
        """
        if firm_value is None:
            return self.config.penalty_amount

        # Check if flexible penalty system is configured
        has_fixed = self.config.penalty_fixed > 0
        has_pct = self.config.penalty_percentage > 0

        if not has_fixed and not has_pct:
            # Flexible system not configured — use flat penalty
            penalty = self.config.penalty_amount
        else:
            # Flexible: max(fixed floor, percentage × revenue)
            fixed = self.config.penalty_fixed
            pct_penalty = self.config.penalty_percentage * firm_value
            penalty = max(fixed, pct_penalty)

        # Apply ceiling (limited liability bound) if set
        if self.config.penalty_ceiling is not None:
            penalty = min(penalty, self.config.penalty_ceiling)

        return penalty

    def apply_penalty(
        self, violation_found: bool, firm_value: float | None = None
    ) -> float:
        """Compute the penalty based on audit outcome.

        Args:
            violation_found: Whether the audit found a violation.
            firm_value: The firm's economic value (M$) for flexible penalty.
                If None, falls back to flat penalty_amount.

        Returns:
            The penalty amount if violation found, 0.0 otherwise.
        """
        if violation_found:
            return self.compute_penalty_amount(firm_value)
        return 0.0
