"""Mesa model integration for the Compute Permit Simulator."""

import random

import mesa

from ..domain.agents import Lab
from ..domain.enforcement import Governor
from ..domain.market import SimpleClearingMarket
from ..schemas import ScenarioConfig


class MesaLab(mesa.Agent):
    """Mesa wrapper for the Lab domain logic."""

    def __init__(
        self,
        unique_id: int,
        model: mesa.Model,
        gross_value: float,
        risk_profile: float,
        capability_value: float = 0.0,
        racing_factor: float = 1.0,
        reputation_sensitivity: float = 0.0,
        audit_coefficient: float = 1.0,
    ) -> None:
        super().__init__(model)
        self.unique_id = unique_id
        self.domain_agent = Lab(
            unique_id,
            gross_value,
            risk_profile,
            capability_value=capability_value,
            racing_factor=racing_factor,
            reputation_sensitivity=reputation_sensitivity,
            audit_coefficient=audit_coefficient,
        )
        self.wealth: float = 0.0

    def step(self) -> None:
        """Execute one step of the agent.

        Note: Model controls phase order explicitly.
        step() might be empty if Model orchestrates phases.
        We let Model orchestrate phases (trade, run, etc.) to ensure strict order.
        """
        pass


class ComputePermitModel(mesa.Model):
    """The central Mesa model."""

    def __init__(self, config: ScenarioConfig) -> None:
        """Initialize the model.

        Args:
            config: Full scenario configuration.
        """
        super().__init__(seed=config.seed)
        self.config = config
        self.n_agents = config.n_agents
        # Mesa 3.x handles agent management via self.agents automatically
        self.running = True

        # Initialize Market and Governor
        self.market = SimpleClearingMarket(token_cap=config.market.token_cap)
        if config.market.fixed_price is not None:
            self.market.set_fixed_price(config.market.fixed_price)
        self.governor = Governor(config.audit)

        # Initialize Agents
        for i in range(self.n_agents):
            gross_value = random.uniform(
                config.lab.gross_value_min, config.lab.gross_value_max
            )
            risk_profile = random.uniform(
                config.lab.risk_profile_min, config.lab.risk_profile_max
            )
            # Pass all extended parameters to the agent
            MesaLab(
                i,
                self,
                gross_value,
                risk_profile,
                capability_value=config.lab.capability_value,
                racing_factor=config.lab.racing_factor,
                reputation_sensitivity=config.lab.reputation_sensitivity,
                audit_coefficient=config.lab.audit_coefficient,
            )
            # Agent is automatically added to self.agents in Mesa 3.x

        # Data Collection
        from .data_collect import compute_average_price, compute_compliance_rate

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Compliance_Rate": compute_compliance_rate,
                "Price": compute_average_price,
            }
        )

    def step(self) -> None:
        """Execute one step of the simulation (matches Game Loop)."""
        # 1. Trading Phase
        # Collect bids (valuations) from all agents
        # For simplicity, valuation ~ gross_value (assume 1 permit needed)
        # Bids are tuples of (lab_id, valuation)
        bids = [
            (a.domain_agent.lab_id, a.domain_agent.get_bid())
            for a in self.agents
            if isinstance(a, MesaLab)
        ]

        # Market handles price discovery and allocation
        clearing_price, winning_ids = self.market.allocate(bids)

        # Apply results to agents
        winning_set = set(winning_ids)
        for agent in self.agents:
            if isinstance(agent, MesaLab):
                if agent.domain_agent.lab_id in winning_set:
                    agent.domain_agent.has_permit = True
                    agent.wealth -= clearing_price
                else:
                    agent.domain_agent.has_permit = False

        # 2. Choice Phase (Run / Compliance)
        # TPR = 1 - FNR (beta)
        tpr = 1.0 - self.config.audit.false_negative_rate
        p_s = (
            tpr * self.config.audit.high_prob
            + (1.0 - tpr) * self.config.audit.base_prob
        )
        detection_prob = p_s + (1.0 - p_s) * self.config.audit.backcheck_prob

        for agent in self.agents:
            if isinstance(agent, MesaLab):
                agent.domain_agent.decide_compliance(
                    market_price=clearing_price,
                    penalty=self.config.audit.penalty_amount,
                    detection_prob=detection_prob,
                    # cost ignored for MVP or folded into net value
                )

        # 3. Signal Phase & 4. Enforcement Phase
        for agent in self.agents:
            if isinstance(agent, MesaLab):
                is_compliant = agent.domain_agent.is_compliant
                signal = self.governor.generate_signal(is_compliant)
                is_audited = self.governor.decide_audit(signal)

                if is_audited:
                    # Enforce
                    if not is_compliant and not agent.domain_agent.has_permit:
                        # Caught cheating!
                        agent.wealth -= self.config.audit.penalty_amount
                    # If compliant, maybe refund? (Spec mentions refunds)

        self.datacollector.collect(self)
