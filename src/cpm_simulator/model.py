import mesa
from .agents import FirmAgent
from .market import PermitMarket


class ComputePermitMarketModel(mesa.Model):
    """
    A model simulating the Compute Permit Market.
    """

    def __init__(self, N, detection_probability=0.1, penalty=100.0, seed=None):
        super().__init__(seed=seed)
        self.num_agents = N
        self.detection_probability = detection_probability
        self.penalty = penalty
        self.market = PermitMarket()
        
        # Create agents
        for i in range(self.num_agents):
            compute_cap = 100.0 # Placeholder capacity
            FirmAgent(self, compute_capacity=compute_cap)

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Price": lambda m: m.market.current_price,
                "Compliance_Rate": compute_compliance_rate
            },
            agent_reporters={"Compliance": "is_compliant"}
        )

    def step(self):
        """Advance the model by one step."""
        self.market.step()
        self.agents.shuffle_do("step")
        self.datacollector.collect(self)

def compute_compliance_rate(model):
    agents = model.agents
    compliant_count = sum([1 for a in agents if a.is_compliant])
    return compliant_count / len(agents) if len(agents) > 0 else 0
