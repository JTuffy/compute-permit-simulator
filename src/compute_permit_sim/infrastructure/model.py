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
        self, unique_id: int, model: mesa.Model, gross_value: float, risk_profile: float
    ) -> None:
        super().__init__(model)
        self.unique_id = unique_id
        self.domain_agent = Lab(unique_id, gross_value, risk_profile)
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
        self.governor = Governor(config.audit)

        # Initialize Agents
        for i in range(self.n_agents):
            gross_value = random.uniform(
                config.lab.gross_value_min, config.lab.gross_value_max
            )
            risk_profile = random.uniform(
                config.lab.risk_profile_min, config.lab.risk_profile_max
            )
            MesaLab(i, self, gross_value, risk_profile)
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
        bids = [
            a.domain_agent.gross_value for a in self.agents if isinstance(a, MesaLab)
        ]
        clearing_price = self.market.resolve_price(bids)

        # Allocate permits based on bids vs price
        # Agents who value it > price get a permit
        # Re-do allocation properly:
        # Sort agents by value
        sorted_agents = sorted(
            [a for a in self.agents if isinstance(a, MesaLab)],
            key=lambda x: x.domain_agent.gross_value,
            reverse=True,
        )

        permits_available = int(self.market.max_supply)
        for i, agent in enumerate(sorted_agents):
            if (
                i < permits_available
                and agent.domain_agent.gross_value >= clearing_price
            ):
                agent.domain_agent.has_permit = True
                agent.wealth -= clearing_price
            else:
                agent.domain_agent.has_permit = False

        # 2. Choice Phase (Run / Compliance)
        detection_prob = (
            self.config.audit.signal_tpr * self.config.audit.high_prob
            + (1 - self.config.audit.signal_tpr) * self.config.audit.base_prob
        )  # Simplified p_eff for agent decision

        for agent in self.agents:
            if isinstance(agent, MesaLab):
                agent.domain_agent.decide_compliance(
                    market_price=clearing_price,
                    penalty=self.config.audit.penalty_amount,
                    detection_prob=detection_prob,
                    # cost ignored for MVP or folded into net value
                )

        # 3. Signal Phase & 4. Enforcement Phase
        # Collect candidates first to enforce budget
        audit_candidates = []

        for agent in self.agents:
            if isinstance(agent, MesaLab):
                is_compliant = agent.domain_agent.is_compliant
                signal = self.governor.generate_signal(is_compliant)
                # Governor decides if they WANT to audit this agent
                should_audit = self.governor.decide_audit(signal)

                if should_audit:
                    # Queue for budget check
                    # We store 'signal' to prioritize high suspicion (signal=True)
                    audit_candidates.append((agent, signal, is_compliant))

        # Sort candidates: Signal=True (1) first, then Signal=False (0)
        # Randomize order within same priority to be fair
        random.shuffle(audit_candidates)
        audit_candidates.sort(key=lambda x: x[1], reverse=True)

        # Apply Budget
        budget = self.config.audit.audit_budget
        audits_conducted = 0

        for agent, signal, is_compliant in audit_candidates:
            if audits_conducted >= budget:
                break

            # Perform Audit / Enforcement
            audits_conducted += 1
            if not is_compliant and not agent.domain_agent.has_permit:
                # Caught cheating!
                agent.wealth -= self.config.audit.penalty_amount

        self.datacollector.collect(self)
