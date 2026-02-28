"""Enforcement logic for the Auditor.

Implements a two-stage audit model where all detection channels are nested
within the audit event:

Stage 1 — AUDIT OCCURRENCE: Will the firm be audited?
    signal = min(1.0, (excess_compute / flop_threshold) ^ signal_exponent)

    When signal_dependent=True:
        p_audit = min(1.0, base_prob + c(i) × signal × (1.0 - base_prob))
    When signal_dependent=False (pure random auditing):
        p_audit = base_prob

    base_prob is a true floor applied equally to all firms (random audits).
    c(i) only scales the signal-dependent component, so firm-specific audit
    rate differences arise from violation visibility, not the random baseline.

    Budget-capped mode (max_audits_per_step set):
      - signal_dependent=True:  rank triggered labs by signal desc, take top N
      - signal_dependent=False: random sample N from triggered labs

Stage 2 — AUDIT OUTCOME: Given an audit, is the violation found?
    All detection channels (audit pass, backcheck, whistleblower, monitoring)
    are treated as nested within the audit event:

        miss = FNR × (1 - backcheck_prob) × (1 - p_w) × (1 - p_m)
        p_stage2 = 1 - miss

    p_total = p_audit × p_stage2
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
        self.config = config
        self._rng = rng

    def _random(self) -> float:
        """Get a random float using the configured RNG or global random."""
        if self._rng is not None:
            return self._rng.random()
        return random.random()

    # ------------------------------------------------------------------
    # Stage 1: Signal & Audit Occurrence
    # ------------------------------------------------------------------

    def compute_signal(
        self,
        excess_compute: float,
        flop_threshold: float,
    ) -> float:
        """Compute suspicion signal from unpermitted excess compute.

        Formula: signal = min(1.0, (excess / threshold) ^ exponent)

        Args:
            excess_compute: Unpermitted FLOPs above what permits cover (>=0).
            flop_threshold: Regulatory threshold requiring permits.

        Returns:
            Signal strength in [0, 1].
        """
        if excess_compute <= 0:
            return 0.0
        if flop_threshold <= 0:
            return 1.0
        raw_ratio = excess_compute / flop_threshold
        return min(1.0, raw_ratio**self.config.signal_exponent)

    def compute_audit_probability(
        self,
        signal: float,
        audit_coefficient: float = 1.0,
    ) -> float:
        """Compute the probability of an audit occurring for one firm.

        When signal_dependent=True:
            p_audit = min(1.0, base_prob + c(i) × signal × (1.0 - base_prob))
        When signal_dependent=False:
            p_audit = base_prob

        base_prob is a uniform floor for all firms (random audits). c(i) only
        scales the signal component, so firm-specific differences arise from
        violation visibility. When signal_dependent=False, c(i) has no effect.

        Args:
            signal: Suspicion signal in [0, 1] from compute_signal().
            audit_coefficient: Firm-specific scaling factor c(i).

        Returns:
            Audit probability in [0, 1].
        """
        if self.config.signal_dependent:
            return min(
                1.0,
                self.config.base_prob
                + audit_coefficient * signal * (1.0 - self.config.base_prob),
            )
        return self.config.base_prob

    # ------------------------------------------------------------------
    # Stage 2: Audit Outcome
    # ------------------------------------------------------------------

    def compute_catch_probability(self, p_w: float = 0.0, p_m: float = 0.0) -> float:
        """Probability of catching a real violation once audited (Stage 2).

        All detection channels are nested within the audit event:
            miss = FNR × (1 - backcheck_prob) × (1 - p_w) × (1 - p_m)
            p_stage2 = 1 - miss

        Args:
            p_w: Whistleblower detection probability (within the audit).
            p_m: Monitoring detection probability (within the audit).

        Returns:
            Catch probability in [0, 1].
        """
        fnr = self.config.false_negative_rate
        backcheck = self.config.backcheck_prob
        miss = fnr * (1.0 - backcheck) * (1.0 - p_w) * (1.0 - p_m)
        return 1.0 - miss

    def audit_detection_channel(
        self,
        is_compliant: bool,
        p_w: float = 0.0,
        p_m: float = 0.0,
    ) -> tuple[bool, bool]:
        """Run the full audit outcome and return (caught, caught_via_backcheck).

        All detection channels (direct audit, backcheck, whistleblower,
        monitoring) are resolved together as part of one audit event.

        Sequential logic preserves the aggregate catch probability from
        compute_catch_probability(p_w, p_m):
            1. Direct pass:   P = 1 - FNR
            2. Backcheck:     P = backcheck_prob  (only if direct missed)
            3. Whistleblower: P = p_w  (only if steps 1-2 both missed)
            4. Monitoring:    P = p_m  (only if steps 1-3 all missed)

        Args:
            is_compliant: True if the firm has no real violation.
            p_w: Whistleblower detection probability.
            p_m: Monitoring detection probability.

        Returns:
            Tuple (caught, caught_via_backcheck):
                caught             — True if any channel found a violation
                caught_via_backcheck — True if the backcheck specifically fired
        """
        if is_compliant:
            # False positive: same sequential structure as non-compliant.
            # p_w/p_m don't apply (no real violation to find via those channels).
            if self._random() < self.config.false_positive_rate:
                return True, False  # false positive on direct pass
            caught_backcheck = self._random() < self.config.backcheck_prob
            return caught_backcheck, caught_backcheck

        # Steps 3-4: whistleblower and monitoring fire within the audit event,
        # catching violations the direct pass and backcheck missed.
        caught_wb = self._random() < p_w
        caught_mon = self._random() < p_m

        # Step 1: direct audit pass
        caught_direct = self._random() < (1.0 - self.config.false_negative_rate)

        # Step 2: backcheck (only runs if the direct pass missed)
        caught_backcheck = False
        if not caught_direct:
            caught_backcheck = self._random() < self.config.backcheck_prob

        caught = caught_direct or caught_backcheck or caught_wb or caught_mon
        return caught, caught_backcheck

    def audit_finds_violation(self, is_compliant: bool) -> bool:
        """Convenience wrapper — returns only the boolean from audit_detection_channel."""
        found, _ = self.audit_detection_channel(is_compliant)
        return found

    # ------------------------------------------------------------------
    # Combined: Detection probability (for firm compliance decisions)
    # ------------------------------------------------------------------

    def compute_detection_probability(
        self,
        excess_compute: float,
        flop_threshold: float,
        audit_coefficient: float = 1.0,
        p_w: float = 0.0,
        p_m: float = 0.0,
    ) -> float:
        """Compute total detection probability for a firm.

        Combines Stage 1 (audit occurrence) with Stage 2 (catch if audited).
        Whistleblower and monitoring are nested within the audit outcome:
            p_detection = p_audit × p_stage2(p_w, p_m)

        Args:
            excess_compute: Unpermitted FLOPs above what permits cover.
            flop_threshold: Regulatory threshold requiring permits.
            audit_coefficient: Firm-specific scaling factor c(i).
            p_w: Whistleblower detection probability (within the audit).
            p_m: Monitoring detection probability (within the audit).

        Returns:
            Total detection probability in [0, 1].
        """
        signal = self.compute_signal(excess_compute, flop_threshold)
        p_audit = self.compute_audit_probability(signal, audit_coefficient)
        p_stage2 = self.compute_catch_probability(p_w=p_w, p_m=p_m)
        return p_audit * p_stage2

    # ------------------------------------------------------------------
    # Penalty computation
    # ------------------------------------------------------------------

    def apply_penalty(self, violation_found: bool, penalty_amount: float) -> float:
        """Return the penalty if a violation was found.

        The penalty amount is a per-firm attribute; the auditor only decides
        whether the violation was caught, not what the penalty is.

        Args:
            violation_found: Whether the audit found a violation.
            penalty_amount: The firm's configured penalty (M$).

        Returns:
            penalty_amount if violation_found, else 0.0.
        """
        return penalty_amount if violation_found else 0.0
