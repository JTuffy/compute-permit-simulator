"""Agent / Lab logic for compliance decisions.

Implements the standard deterrence model:
    Compliance condition: p * B >= g
    where p = detection probability, B = total penalty, g = gain from cheating.

    Ref: technical_specification.md Section 2.1 "Agents (Labs)"
"""


class Lab:
    """Represents an AI Lab (Firm).

    Attributes:
        lab_id: Unique identifier.
        gross_value: The value (v_i) the lab generates from a training run.
        risk_profile: Multiplier on perceived penalty
            (>1 = risk-averse, <1 = risk-seeking).
        capability_value: V_b, baseline value of model capabilities from training.
        racing_factor: c_r, urgency multiplier on capability value.
        reputation_sensitivity: R, perceived reputation cost if caught.
        audit_coefficient: c(i), firm-specific scaling on base audit rate.
        is_compliant: State of the last compliance decision.
        has_permit: Whether the lab holds a valid permit this period.
    """

    def __init__(
        self,
        lab_id: int,
        gross_value: float,
        risk_profile: float = 1.0,
        capability_value: float = 0.0,
        racing_factor: float = 1.0,
        reputation_sensitivity: float = 0.0,
        audit_coefficient: float = 1.0,
    ) -> None:
        """Initialize the Lab.

        Args:
            lab_id: Unique ID.
            gross_value: v_i, value of the training run.
            risk_profile: Multiplier for perceived penalty (default 1.0).
            capability_value: V_b, baseline capability value (default 0.0).
            racing_factor: c_r, urgency multiplier (default 1.0).
            reputation_sensitivity: R, reputation cost if caught (default 0.0).
            audit_coefficient: c(i), firm-specific audit scaling (default 1.0).
        """
        self.lab_id: int = lab_id
        self.gross_value: float = gross_value
        self.risk_profile: float = risk_profile
        self.capability_value: float = capability_value
        self.racing_factor: float = racing_factor
        self.reputation_sensitivity: float = reputation_sensitivity
        self.audit_coefficient: float = audit_coefficient
        self.is_compliant: bool = True
        self.has_permit: bool = False
        # Monitoring / specific state
        self.last_gain: float = 0.0
        self.last_expected_penalty: float = 0.0

    def get_bid(self, cost: float = 0.0) -> float:
        """Return willingness to pay for a permit.

        Args:
            cost: Operational cost (c) deducted from gross value.

        Returns:
            Non-negative bid value.
        """
        return max(0.0, self.gross_value - cost)

    def decide_compliance(
        self,
        market_price: float,
        penalty: float,
        detection_prob: float,
        cost: float = 0.0,
    ) -> bool:
        """Decide whether to comply, applying the deterrence condition p * B >= g.

        Decision logic (Emlyn deterrence doc p.1):
            1. If has_permit -> compliant (already paid for legal usage).
            2. Compute gain from cheating: g = delta_c + V.
            3. If g <= 0 -> compliant (no incentive to cheat).
            4. Compute perceived penalty:
               B_total = (penalty + reputation) * risk_profile.
            5. If detection_prob * B_total >= g -> compliant (deterred).
            6. Otherwise -> non-compliant (cheat).

        Args:
            market_price: Current permit price (used as delta_c for binary q).
            penalty: The effective penalty amount (P).
            detection_prob: Effective detection probability (p_eff).
            cost: Operational cost (c).

        Returns:
            True if compliant, False if non-compliant.
        """
        # 1. Permitted firms are compliant
        if self.has_permit:
            self.is_compliant = True
            self.last_gain = 0.0
            self.last_expected_penalty = 0.0
            return True

        # 2. Gain from cheating: g = delta_c + V
        #    delta_c = market_price (savings from not buying permit)
        #    BUT if v_i < market_price, the agent wouldn't buy anyway.
        #    So the benefit of cheating is getting to run
        #    (worth v_i) vs not running (0).
        #    Thus effective delta_c = min(market_price, self.gross_value)
        delta_c = min(market_price, self.gross_value)
        capability_gain = self.racing_factor * self.capability_value
        gain = delta_c + capability_gain
        # Store for UI
        self.last_gain = gain

        # 3. No gain -> compliant (don't run or no incentive)
        if gain <= 0:
            self.is_compliant = True
            self.last_expected_penalty = 0.0
            return True

        # Also check: is running profitable at all?
        # If gross_value - cost <= 0, the firm wouldn't run regardless
        if self.gross_value - cost <= 0:
            self.is_compliant = True
            self.last_expected_penalty = 0.0
            return True

        # 4. Perceived total penalty: B = (penalty + reputation) * risk_profile
        b_total = (penalty + self.reputation_sensitivity) * self.risk_profile

        # 5. Deterrence condition: p * B >= g
        # Effective P for this agent includes their specific audit profile
        agent_specific_prob = detection_prob * self.audit_coefficient
        expected_penalty = agent_specific_prob * b_total

        # Store for UI
        self.last_expected_penalty = expected_penalty

        if expected_penalty >= gain:
            self.is_compliant = True
            return True

        # 6. Not deterred -> cheat
        self.is_compliant = False
        return False
