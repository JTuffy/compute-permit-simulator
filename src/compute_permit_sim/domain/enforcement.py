"""Enforcement logic for the Governor/Auditor."""

import random
from dataclasses import dataclass


@dataclass
class AuditConfig:
    """Configuration for audit policies."""

    base_prob: float  # pi_0
    high_prob: float  # pi_1 (targeted)
    signal_fpr: float  # alpha
    signal_tpr: float  # beta
    penalty_amount: float  # P
    audit_budget: int = 5  # Max audits per step


class Governor:
    """The Governor agent handling audits and enforcement."""

    def __init__(self, config: AuditConfig) -> None:
        """Initialize the Governor.

        Args:
            config: Audit configuration parameters.
        """
        self.config = config

    def generate_signal(self, is_compliant: bool) -> bool:
        """Generate a noisy signal based on compliance status.

        Args:
            is_compliant: True if the lab is compliant (clean).

        Returns:
            True if a 'suspicious' signal is observed (s=1), False otherwise (s=0).
        """
        if is_compliant:
            # False Positive: Compliant but signal = 1
            return random.random() < self.config.signal_fpr
        else:
            # True Positive: Non-compliant and signal = 1
            return random.random() < self.config.signal_tpr

    def decide_audit(self, signal: bool) -> bool:
        """Decide whether to audit based on the signal.

        Policy:
            If signal=1 (High Suspicion) -> Audit with prob pi_1
            If signal=0 (Low Suspicion) -> Audit with prob pi_0

        Args:
            signal: The observed signal value.

        Returns:
            True if an audit is triggered.
        """
        prob = self.config.high_prob if signal else self.config.base_prob
        return random.random() < prob
