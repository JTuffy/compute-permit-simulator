"""Enforcement logic for the Auditor.

Implements the signal-contingent audit model from the technical specification:
    - Auditor observes noisy signal s_i in {0, 1} per firm.
    - P(s=1 | compliant)     = false_positive_rate (alpha)
    - P(s=0 | non-compliant) = false_negative_rate (1 - beta)
    - Audit triggered with pi_1 (high suspicion) or pi_0 (low suspicion).

Effective detection probability (tech spec section 3):
    p_s  = beta * pi_1 + (1 - beta) * pi_0
    p_eff = p_s + (1 - p_s) * backcheck_prob
"""

import random

from ..schemas import AuditConfig


class Auditor:
    """The Auditor agent handling audits and enforcement.

    Attributes:
        config: Audit policy configuration.
    """

    def __init__(self, config: AuditConfig) -> None:
        """Initialize the Auditor.

        Args:
            config: Audit configuration parameters.
        """
        self.config = config

    def compute_effective_detection(self, audit_coefficient: float = 1.0) -> float:
        """Compute the effective detection probability for a firm.

        Formula (Emlyn deterrence doc p.1, tech spec section 3):
            beta = 1 - false_negative_rate  (true positive rate)
            p_s  = beta * pi_1 + (1 - beta) * pi_0
            p_s  = p_s * audit_coefficient   (firm-specific scaling)
            p_eff = p_s + (1 - p_s) * backcheck_prob

        Args:
            audit_coefficient: Firm-specific scaling factor c(i)
                for audit rate.

        Returns:
            The effective detection probability p_eff in [0, 1].
        """
        beta = 1.0 - self.config.false_negative_rate
        p_s = beta * self.config.high_prob + (1.0 - beta) * self.config.base_prob
        p_s = min(1.0, p_s * audit_coefficient)
        p_eff = p_s + (1.0 - p_s) * self.config.backcheck_prob
        return p_eff

    def generate_signal(self, is_compliant: bool) -> bool:
        """Generate a noisy signal based on compliance status.

        Args:
            is_compliant: True if the lab is compliant (clean).

        Returns:
            True if a suspicious signal is observed (s=1),
            False otherwise (s=0).
        """
        if is_compliant:
            # False Positive: compliant but signal = 1
            return random.random() < self.config.false_positive_rate
        else:
            # True Positive: non-compliant and signal = 1
            # P(s=1 | non-compliant) = 1 - false_negative_rate = beta
            return random.random() < (1.0 - self.config.false_negative_rate)

    def decide_audit(self, signal: bool) -> bool:
        """Decide whether to audit based on the signal.

        Policy:
            signal=1 (high suspicion) -> audit with prob pi_1
            signal=0 (low suspicion)  -> audit with prob pi_0

        Args:
            signal: The observed signal value.

        Returns:
            True if an audit is triggered.
        """
        prob = self.config.high_prob if signal else self.config.base_prob
        return random.random() < prob

    def apply_penalty(self, is_compliant: bool, has_permit: bool) -> float:
        """Compute the penalty for a firm that was audited.

        Args:
            is_compliant: Whether the firm complied this period.
            has_permit: Whether the firm holds a valid permit.

        Returns:
            The penalty amount to deduct from the firm's wealth.
            Returns 0.0 if the firm is compliant or holds a permit.
        """
        if is_compliant or has_permit:
            return 0.0
        return self.config.penalty_amount
