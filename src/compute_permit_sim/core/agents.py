"""Agent / Lab logic for compliance decisions.

Implements the standard deterrence model:
    Compliance condition: p * B >= g
    where p = detection probability, B = total penalty, g = gain from cheating.

    Ref: technical_specification.md Section 2.1 "Agents (Labs)"
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..schemas import LabConfig

logger = logging.getLogger(__name__)


class Lab:
    """Represents an AI Lab (Firm).

    Attributes:
        lab_id: Unique identifier.
        economic_value: The value (v_i) the lab generates from a training run.
        risk_profile: Multiplier on perceived penalty
            (>1 = risk-averse, <1 = risk-seeking).
        planned_training_flops: Planned training run size (FLOP).
        penalty_amount: Flat penalty if caught (M$).
        capability_value: V_b, baseline value of model capabilities from training.
        racing_factor: c_r, urgency multiplier on capability value.
        reputation_sensitivity: R, perceived reputation cost if caught.
        audit_coefficient: c(i), firm-specific scaling on base audit rate.
        is_compliant: State of the last compliance decision.
        permits_held: Number of permits held this period (0 = none).
    """

    def __init__(
        self,
        lab_id: int,
        config: "LabConfig",
        economic_value: float,
        risk_profile: float,
        planned_training_flops: float = 0.0,
        penalty_amount: float = 0.0,
    ) -> None:
        self.lab_id: int = lab_id
        self.economic_value: float = economic_value
        self.risk_profile: float = risk_profile
        self.planned_training_flops: float = planned_training_flops
        self.penalty_amount: float = penalty_amount

        # Static params from config (base values, never modified)
        self.capability_value: float = config.capability_value
        self.base_racing_factor: float = config.racing_factor
        self.racing_factor: float = config.racing_factor
        self.reputation_sensitivity: float = config.reputation_sensitivity
        self.audit_coefficient: float = config.audit_coefficient

        # Dynamic factor config (from LabConfig)
        self.reputation_escalation_factor: float = config.reputation_escalation_factor
        self.racing_gap_sensitivity: float = config.racing_gap_sensitivity
        self.capability_scale: float = config.capability_scale

        # Per-step state
        self.is_compliant: bool = True
        self.permits_held: int = 0  # 0 = no permits; >=1 in multi-unit mode
        self.collateral_posted: float = 0.0  # M$: collateral held this step

        # Dynamic state (evolves over steps)
        self.failed_audit_count: int = 0  # cumulative failed audits
        self.current_audit_coefficient: float = self.audit_coefficient  # may escalate
        self.current_reputation_sensitivity: float = (
            self.reputation_sensitivity
        )  # may escalate
        self.cumulative_capability: float = 0.0  # cumulative successful runs

    @property
    def has_permit(self) -> bool:
        """Whether the lab holds at least one permit."""
        return self.permits_held > 0

    def excess_flops(self, flops_per_permit: float | None) -> float:
        """Compute unpermitted FLOPs above what permits cover.

        Args:
            flops_per_permit: FLOPs covered per permit. None = binary mode
                (any permit covers the full training run).

        Returns:
            Excess FLOPs not covered by held permits (>= 0).
        """
        if flops_per_permit is None:
            # Binary mode: 1 permit covers everything
            return 0.0 if self.permits_held > 0 else self.planned_training_flops
        permitted = self.permits_held * flops_per_permit
        return max(0.0, self.planned_training_flops - permitted)

    def get_bid(self, cost: float = 0.0) -> float:
        """Return willingness to pay for a permit.

        Args:
            cost: Operational cost (c) deducted from gross value.

        Returns:
            Non-negative bid value.
        """
        return max(0.0, self.economic_value - cost)

    def decide_compliance(
        self,
        market_price: float,
        penalty: float,
        detection_prob: float,
        cost: float = 0.0,
    ) -> bool:
        """Decide whether to comply, applying the deterrence condition p * B >= g.

        Called only for labs with unpermitted excess (the game loop skips
        fully-covered labs).  Decision logic:
            1. Compute gain from cheating: g = delta_c + V.
            2. If g <= 0 -> compliant (no incentive to cheat).
            3. Compute perceived penalty:
               B_total = (penalty + collateral + reputation) * risk_profile
               Ref: Christoph (2026) §2.5 — P_eff = K + phi (collateral + fine)
            4. If detection_prob * B_total >= g -> compliant (deterred).
            5. Otherwise -> non-compliant (cheat).

        Args:
            market_price: Current permit price (used as delta_c for binary q).
            penalty: The effective penalty amount (phi, ex post fine).
            detection_prob: Effective detection probability (p_eff).
            cost: Operational cost (c).

        Returns:
            True if compliant, False if non-compliant.
        """
        # 1. Gain from cheating: g = delta_c + V
        #    delta_c = market_price (savings from not buying permit)
        #    BUT if v_i < market_price, the agent wouldn't buy anyway.
        #    So the benefit of cheating is getting to run
        #    (worth v_i) vs not running (0).
        #    Thus effective delta_c = min(market_price, self.economic_value)
        delta_c = min(market_price, self.economic_value)
        capability_gain = self.racing_factor * self.capability_value
        gain = delta_c + capability_gain

        # 2. No gain -> compliant (don't run or no incentive)
        if gain <= 0:
            self.is_compliant = True
            return True

        # Also check: is running profitable at all?
        # If economic_value - cost <= 0, the firm wouldn't run regardless
        if self.economic_value - cost <= 0:
            self.is_compliant = True
            return True

        # 3. Perceived total penalty: B = (penalty + collateral + reputation) * risk_profile
        #    Collateral is seized on violation, so it's part of the effective punishment.
        #    Ref: Christoph (2026) §2.5 — P_eff = K + phi
        #    Uses current_reputation_sensitivity (may be escalated from base via dynamic factors)
        b_total = (
            penalty + self.collateral_posted + self.current_reputation_sensitivity
        ) * self.risk_profile

        # 4. Deterrence condition: p * B >= g
        # detection_prob already incorporates the firm-specific audit coefficient
        # c(i) via auditor.compute_detection_probability() in the game loop.
        expected_penalty = detection_prob * b_total

        logger.debug(
            f"Lab {self.lab_id} Decision: Gain={gain:.3f}, "
            f"Prob={detection_prob:.3f}, B={b_total:.3f}, "
            f"ExpPenalty={expected_penalty:.3f}"
        )

        if expected_penalty >= gain:
            self.is_compliant = True
            return True

        # 5. Not deterred -> cheat
        self.is_compliant = False
        logger.info(
            f"Lab {self.lab_id} CHEATING: Gain ({gain:.3f}) > ExpPenalty ({expected_penalty:.3f})"
        )
        return False

    def on_audit_failure(self, audit_escalation: float = 0.0) -> None:
        """Update dynamic state after being caught in an audit.

        4.1 Reputation: rep_t = base × (1 + factor)^failed_count
        4.2 Audit coefficient: coeff += escalation

        Args:
            audit_escalation: Amount to add to audit coefficient (from AuditConfig).
        """
        self.failed_audit_count += 1

        # 4.1 Reputation escalation
        if self.reputation_escalation_factor > 0:
            self.current_reputation_sensitivity = self.reputation_sensitivity * (
                (1 + self.reputation_escalation_factor) ** self.failed_audit_count
            )

        # 4.2 Audit coefficient escalation
        if audit_escalation > 0:
            self.current_audit_coefficient += audit_escalation

    def decay_audit_coefficient(self, decay_rate: float) -> None:
        """Decay escalated audit coefficient back toward base value.

        Formula: coeff_t = base + (coeff_{t-1} - base) × decay_rate

        Args:
            decay_rate: Per-step decay factor (0.8 = 20% decay per step).
        """
        if self.current_audit_coefficient > self.audit_coefficient:
            excess = self.current_audit_coefficient - self.audit_coefficient
            self.current_audit_coefficient = (
                self.audit_coefficient + excess * decay_rate
            )

    def update_racing_factor(self, mean_capability: float) -> None:
        """Update racing factor based on relative capability position.

        Formula: racing_t = base × (1 + sensitivity × gap / scale)

        Args:
            mean_capability: Mean cumulative capability across all labs.
        """
        if self.racing_gap_sensitivity <= 0:
            return
        gap = self.cumulative_capability - mean_capability
        multiplier = 1.0 + self.racing_gap_sensitivity * gap / self.capability_scale
        self.racing_factor = max(0.0, self.base_racing_factor * multiplier)
