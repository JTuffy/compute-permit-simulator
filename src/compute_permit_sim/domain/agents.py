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
        self,
        lab_id: int,
        gross_value: float,
        risk_profile: float = 1.0,
        capability: float = 10.0,
        allowance: float = 0.0,
        collateral: float = 0.0,
    ) -> None:
        """Initialize the Lab.

        Args:
            lab_id: Unique ID.
            gross_value: v_i - Value of the run (per unit or total? abstract value).
            risk_profile: Modifier for risk calculation (default=1.0).
            capability: Max compute possible (q_max).
            allowance: Initial permits allocated (a_i).
            collateral: Collateral posted (K_i).
        """
        self.lab_id: int = lab_id
        self.gross_value: float = gross_value
        self.risk_profile: float = risk_profile
        self.capability: float = capability
        self.allowance: float = allowance
        self.collateral: float = collateral

        # Compliance State
        self.has_permit: bool = False  # Legacy boolean, transitioning to quanitative
        self.is_compliant: bool = True

        # Quantitative State
        self.true_compute: float = 0.0
        self.reported_compute: float = 0.0

    def decide_strategy(
        self,
        market_price: float,
        penalty: float,
        detection_prob: float,
        cost_per_unit: float = 0.0,
    ) -> tuple[float, float]:
        """Decide Run Size (q) and Reported Size (r).

        Model:
            Maximize U = Benefit(q) - Cost(q) - ExpectedPenalty(q, r)

            Benefit(q): gross_value * q (Assuming linear value scale for MVP)
                        OR gross_value is just a scalar multiplier.
                        Let's assume Benefit = gross_value * q.

            Cost(q): cost_per_unit * q (Operational) + market_price * (q - allowance)?
                     For now, assume Permits are pre-allocated (allowance).
                     If we want to trade later, we add that.

            ExpectedPenalty(q, r):
                If q <= allowance: 0
                If q > allowance:
                    Non-Compliance Amount x = q - allowance
                    But wait, regulator only knows 'r'.

                    If r <= allowance: Looks compliant.
                        But if audited, we are caught if q > allowance.
                        Penalty ~ P * (q - allowance)? Or P fixed?
                        Paper says L (Liability) or P.

                    If r > allowance: Admitting non-compliance.
                        Pay fine immediately? Or buy permits?

            Heuristic Strategy for MVP:
            1. Desired Q: Limit by capability.
               If value is high, push Q to capability.
               If value is low, maybe Q = 0.

            2. Report R:
               If Q <= allowance: Report Q (Honest).
               If Q > allowance:
                   Report allowance (Hide excess).
                   Risk: Audit probability * Penalty.
        """
        # 1. Determine Desired Q (True Compute)
        # Simple Logic: If value > cost, run at max capability.
        # Refined: Run at max unless risk of audit is too high.

        # For MVP: "The Greedy Lab"
        # Always run at max capability if value is positive.
        target_q = self.capability

        # 2. Determine Report R
        # If covered by allowance, report honestly.
        if target_q <= self.allowance:
            target_r = target_q
        else:
            # Not covered. Defect?
            # Decision: Hide the excess?
            # Gap = target_q - allowance.

            # Expected Cost of Cheating:
            # E[Cost] = detection_prob * (Penalty + (target_q - allowance) * Price?)
            # Let's simplify: Expected Penalty = detection_prob * penalty
            # Benefit of Cheating = (target_q - allowance) * Value

            benefit_of_excess = (target_q - self.allowance) * self.gross_value
            cost_of_risk = detection_prob * penalty * self.risk_profile

            if benefit_of_excess > cost_of_risk:
                # Cheat: Run max, Report allowance (hide it)
                target_r = self.allowance
                # Note: We could report 0 to be safer?
                # But reporting allowance uses the permits we have.
            else:
                # Compliant: Restrict Q to allowance
                target_q = self.allowance
                target_r = self.allowance

        self.true_compute = target_q
        self.reported_compute = target_r

        # Legacy flags for compatibility
        self.is_compliant = self.true_compute <= self.allowance + 0.01  # tolerance

        return self.true_compute, self.reported_compute

    # Legacy methods for compatibility (optional, or remove if confident)
    def decide_compliance(self, *args, **kwargs):
        self.decide_strategy(*args, **kwargs)
        return self.is_compliant

    def decide_reporting(self):
        return self.reported_compute
