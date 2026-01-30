"""Model definitions for the Compute Permit Market Simulator."""

import mesa

from .agents import FirmAgent
from .market import PermitMarket


class ComputePermitMarketModel(mesa.Model):
    """A model simulating the Compute Permit Market.

    Attributes:
        num_agents: Number of firm agents in the model.
        detection_probability: Probability of detecting non-compliance.
        penalty: Penalty amount for non-compliance.
        market: The permit market instance.
        datacollector: DataCollector for model and agent data.
    """

    def __init__(
        self,
        n_agents: int,
        detection_probability: float = 0.1,
        penalty: float = 100.0,
        seed: int | None = None,
    ) -> None:
        """Initialize the ComputePermitMarketModel.

        Args:
            n_agents: Number of agents.
            detection_probability: Probability of being caught if cheating.
            penalty: Fine amount if caught cheating.
            seed: Random seed for the model.
        """
        super().__init__(seed=seed)
        self.num_agents: int = n_agents
        self.detection_probability: float = detection_probability
        self.penalty: float = penalty
        self.market: PermitMarket = PermitMarket()

        # Create agents
        for _ in range(self.num_agents):
            compute_cap: float = 100.0  # Placeholder capacity
            FirmAgent(self, compute_capacity=compute_cap)

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Price": lambda m: m.market.current_price,
                "Compliance_Rate": compute_compliance_rate,
            },
            agent_reporters={"Compliance": "is_compliant"},
        )

    def step(self) -> None:
        """Advance the model by one step."""
        self.market.step()
        self.agents.shuffle_do("step")
        self.datacollector.collect(self)


def compute_compliance_rate(model: ComputePermitMarketModel) -> float:
    """Compute the current compliance rate of firm agents.

    Args:
        model: The model instance.

    Returns:
        The fraction of agents that are compliant (0.0 to 1.0).
    """
    agents = model.agents
    if not agents:
        return 0.0

    # Explicit list comprehension for clarity and performance
    compliant_count = sum(1 for a in agents if hasattr(a, "is_compliant") and a.is_compliant)
    return compliant_count / len(agents)
