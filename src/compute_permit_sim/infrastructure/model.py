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
        capability: float,
        allowance: float,
        collateral: float,
    ) -> None:
        super().__init__(model)
        self.unique_id = unique_id
        self.domain_agent = Lab(
            unique_id, gross_value, risk_profile, capability, allowance, collateral
        )
        self.wealth: float = 0.0

    def step(self) -> None:
        pass


class ComputePermitModel(mesa.Model):
    """The central Mesa model."""

    def __init__(self, config: ScenarioConfig) -> None:
        super().__init__(seed=config.seed)
        self.config = config
        self.n_agents = config.n_agents
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
            capability = random.uniform(
                config.lab.capability_min, config.lab.capability_max
            )
            allowance = random.uniform(
                config.lab.allowance_min, config.lab.allowance_max
            )
            collateral = random.uniform(
                config.lab.collateral_min, config.lab.collateral_max
            )

            MesaLab(
                i, self, gross_value, risk_profile, capability, allowance, collateral
            )

        # Data Collection
        # Note: We might need to update reporters to average "True Compute"
        # instead of compliance rate later. Keeping as is for now.
        from .data_collect import compute_average_price, compute_compliance_rate

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Compliance_Rate": compute_compliance_rate,
                "Price": compute_average_price,
            }
        )

    def step(self) -> None:
        """Execute one step of the simulation (Quantitative Mode)."""

        # 1. Allocation Phase (Grandfathered / Market)
        # For this version, allowance is fixed per agent (Grandfathered).
        # We skip trading loop for now to focus on Reporting Game.
        # Future: Allow trading of 'allowance'.

        # Current Price is static or 0 in this mode?
        # Let's say price is 0 for grandfathered permits.
        clearing_price = 0.0

        # Update Market State (just for visualization consistency)
        # Sum of allowances = Total Supply
        total_supply = sum(
            a.domain_agent.allowance for a in self.agents if isinstance(a, MesaLab)
        )
        self.market.max_supply = total_supply
        self.market.current_price = clearing_price

        # 2. Strategy Phase (Run Design & Reporting)
        dp_high = self.config.audit.signal_tpr * self.config.audit.high_prob
        dp_base = (1 - self.config.audit.signal_tpr) * self.config.audit.base_prob
        detection_prob = dp_high + dp_base

        for agent in self.agents:
            if isinstance(agent, MesaLab):
                agent.domain_agent.decide_strategy(
                    market_price=clearing_price,
                    penalty=self.config.audit.penalty_amount,
                    detection_prob=detection_prob,
                )

        # 3. Enforcement Phase
        # Collect candidates based on REPORTED vs EXPECTED?
        # Or derived signals.
        # Current logic: Signal derived from 'is_compliant'.
        # We need to map quantitative to 'is_compliant' flag for compatibility.
        # Agent logic handles this: is_compliant = (true <= allowance).

        candidates = []

        for agent in self.agents:
            if isinstance(agent, MesaLab):
                # Derived Signal from Energy vs Report
                true_q = agent.domain_agent.true_compute
                reported_r = agent.domain_agent.reported_compute

                # Governor observes Energy (noisy q) vs Reported
                signal = self.governor.generate_signal(true_q, reported_r)
                should_audit = self.governor.decide_audit(signal)

                if should_audit:
                    candidates.append((agent, signal, agent.domain_agent.is_compliant))

        audit_queue = self.governor.apply_budget(candidates)

        for agent, signal, is_compliant in audit_queue:
            # Audit Check: True Compute vs Allowance
            violation_amount = (
                agent.domain_agent.true_compute - agent.domain_agent.allowance
            )

            if violation_amount > 0.01:  # Tolerance
                # Caught cheating!
                # Fine might be fixed or proportional?
                # Spec says fixed P for now.
                agent.wealth -= self.config.audit.penalty_amount
                # Seize Collateral
                collateral_seized = agent.domain_agent.collateral
                agent.wealth -= collateral_seized

                # Note: We don't remove the agent from the game, just penalize wealth.
                # In full sim, if wealth < 0, they might exit.

        self.datacollector.collect(self)
