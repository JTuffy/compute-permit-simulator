"""Agent definitions for the Compute Permit Market Simulator."""

import mesa

# from .market import PermitMarket  # Unused import


class FirmAgent(mesa.Agent):
    """A firm that requires compute permits to operate.

    Attributes:
        compute_capacity: The maximum compute capacity/emissions of the firm.
        risk_attitude: Multiplier for risk sensitivity (higher = more risk-seeking).
        permits_held: The number of permits currently held by the firm.
        is_compliant: Boolean indicating if the firm decided to comply this step.
        emissions: The actual emissions (or compute usage) for the current step.
    """

    def __init__(self, model: mesa.Model, compute_capacity: float, risk_attitude: float = 1.0) -> None:
        """Initialize the FirmAgent.

        Args:
            model: The parent model instance.
            compute_capacity: The maximum compute capacity of the firm.
            risk_attitude: Risk attitude parameter (default: 1.0).
        """
        super().__init__(model)
        self.compute_capacity: float = compute_capacity
        self.risk_attitude: float = risk_attitude
        self.permits_held: float = 0.0
        self.is_compliant: bool = True
        self.emissions: float = 0.0

    def step(self) -> None:
        """Execute the agent's decision loop for one step.

        Process:
            1. Determine compute/emission needs.
            2. Decide whether to comply based on expected costs vs gains.
            3. Interact with the market (buy permits if compliant).
        """
        # 1. Determine Needs (Simplified: use full capacity)
        self.emissions = self.compute_capacity

        # 2. Compliance Decision
        # Formula: Comply if Expected Cost of Non-Compliance > Expected Gain
        # p * B >= g
        # We can implement this as: if p * B < g, then Cheat (Non-Comply)

        p: float = self.model.detection_probability
        penalty: float = self.model.penalty  # Renamed B to penalty
        # Gain g is the cost savings from not buying permits (or profit boost)
        market_price: float = self.model.market.current_price
        gain: float = self.emissions * market_price

        expected_penalty: float = p * penalty

        if expected_penalty < gain:
            self.is_compliant = False
        else:
            self.is_compliant = True

        # 3. Market Interaction
        if self.is_compliant:
            required_permits: float = self.emissions - self.permits_held
            if required_permits > 0:
                # Buy permits
                # In MVP, we assume they just pay the market price
                self.permits_held += required_permits
                # self.wealth -= required_permits * market_price
        # else:
        # Not compliant: Don't buy permits for the uncovered amount


class RegulatorAgent(mesa.Agent):
    """Represents regulatory actions if they need to be agent-based.

    Currently a placeholder for future regulatory logic.
    """

    def __init__(self, model: mesa.Model) -> None:
        """Initialize the RegulatorAgent.

        Args:
            model: The parent model instance.
        """
        super().__init__(model)

    def step(self) -> None:
        """Execute regulator actions for the step."""
