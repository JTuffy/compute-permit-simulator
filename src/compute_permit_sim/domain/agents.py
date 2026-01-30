"""Agent / Lab logic for compliance interactions."""


class Lab:
    """Represents an AI Lab (Firm).

    Attributes:
        lab_id: Unique identifier.
        gross_value: The value (v_i) the lab generates from a training run.
        risk_profile: Logic/parameter determining risk sensitivity.
        is_compliant: State of the last decision.
    """

    def __init__(
        self, lab_id: int, gross_value: float, risk_profile: float = 1.0
    ) -> None:
        """Initialize the Lab.

        Args:
            lab_id: Unique ID.
            gross_value: v_i - Value of the run.
            risk_profile: Modifier for risk calculation (default=1.0).
        """
        self.lab_id: int = lab_id
        self.gross_value: float = gross_value
        self.risk_profile: float = risk_profile
        self.is_compliant: bool = True
        self.has_permit: bool = False

    def decide_compliance(
        self,
        market_price: float,
        penalty: float,
        detection_prob: float,
        cost: float = 0.0,
    ) -> bool:
        """Decide whether to comply (buy permit) or defect (run without permit).

        Decision Rule:
            If unpermitted, run if: v_i - c > Expected Penalty
            Expected Penalty = P * (beta * pi_1 + (1-beta) * pi_0)
            Or simplified: P * detection_prob

        Args:
            market_price: Current cost of a permit (p).
            penalty: The effective penalty (P).
            detection_prob: The effective probability of detection (p_eff).
            cost: Operational cost (c).

        Returns:
            True if compliant (buys permit or doesn't run if priced out),
            False if non-compliant (runs without permit).
        """
        # Net value of running legally
        profit_legal = self.gross_value - cost - market_price

        # Net value of running illegally (expected)
        expected_penalty = penalty * detection_prob
        # Risk adjustment: A risk-averse agent might weigh penalty higher?
        # Spec says: risk_profile. Scales expected penalty perception?
        # Or perhaps it's just the 'beta' in the spec?
        # For now, we'll treat risk_profile as a multiplier on Disutility of Penalty.
        # Spec: v_i - c > E[Penalty]
        profit_illegal = (self.gross_value - cost) - (
            expected_penalty * self.risk_profile
        )

        # 3 Options:
        # 1. Buy permit (if affordable / creates profit) -> Compliant
        # 2. Don't run (if neither is profitable) -> Compliant (0 emissions)
        # 3. Run illegally -> Non-Compliant

        # If we have a permit, we are compliant (assuming we bought it)
        if self.has_permit:
            return True

        if profit_legal >= 0:
            if profit_legal >= profit_illegal:
                return True
            else:
                return False  # Cheating is more profitable
        else:
            # Legal is not profitable (priced out)
            # Check if illegal is profitable
            if profit_illegal > 0:
                return False  # Cheat
            else:
                return True  # Don't run (Compliant)
