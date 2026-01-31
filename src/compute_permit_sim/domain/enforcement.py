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

    def generate_signal(self, true_compute: float, reported_compute: float) -> bool:
        """Generate a signal based on discrepancy between observed Energy and Report.

        Model:
            Observed Energy E = true_compute + Noise
            Noise ~ Normal(0, sigma)  (For now, we can use simple uniform noise)

            Signal = 1 if (E - reported_compute) > Threshold

            Threshold determination:
            We essentially want to maintain the FPR/TPR from config if possible,
            or we define the threshold dynamically.

            Let's use a simple heuristic for MVP:
            Noise magnitude = 0.5 * true_compute (approx) or fixed amount?

            Let's say Regulator allows some tolerance.
            Discrepancy D = (true_compute + random.gauss(0, 0.1)) - reported_compute

            If D > Tolerance (e.g. 0.2), Signal = True.

        Args:
            true_compute: Actual usage (q).
            reported_compute: What lab reported (r).

        Returns:
            True if suspicious (Signal=1), False otherwise.
        """
        # Noise factor (sigma). Could be config, but hardcoding for MVP
        # to ensure it's 'interesting' relative to the 0-10 scale.
        # Capability is 1-10.
        sigma = 0.5
        noise = random.gauss(0, sigma)

        observed_energy = true_compute + noise

        # Regulator Logic
        # They compare Observed to Reported.
        discrepancy = observed_energy - reported_compute

        # Threshold: How much variance do we tolerate?
        # If strict, threshold = 0. But allows false positives due to noise.
        # We want approx 10% FPR (per config)?
        # For Normal(0, 0.5), 10% tail is at approx 1.28 * sigma = 0.64
        threshold = 0.64

        return discrepancy > threshold

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

    def apply_budget(self, candidates: list) -> list:
        """Filter and sort audit candidates based on budget and priority.

        Args:
            candidates: List of tuples (agent, signal, is_compliant, ...).
                       We expect index 1 to be the signal (bool).

        Returns:
            The subset of candidates to actually audit.
        """
        # Sort: Signal=True (1) first, then Signal=False (0)
        # Randomize order within same priority to be fair
        # Note: In Python, sort is stable. So if we shuffle first, then sort by key,
        # we get randomized groups.
        random.shuffle(candidates)
        candidates.sort(key=lambda x: x[1], reverse=True)

        return candidates[: self.config.audit_budget]
