"""Mesa model integration for the Compute Permit Simulator."""

import random

import mesa

from ..domain.agents import Lab
from ..domain.enforcement import Auditor
from ..domain.market import SimpleClearingMarket
from ..schemas import AuditConfig, LabConfig, MarketConfig, ScenarioConfig


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
        self.was_audited: bool = False
        self.detected_cheating: bool = False

    def step(self) -> None:
        """Execute one step of the agent."""
        pass


class ComputePermitModel(mesa.Model):
    """The central Mesa model."""

    def __init__(self, config: ScenarioConfig = None, **kwargs) -> None:
        """Initialize the model."""
        if config is None:
            config = ScenarioConfig(
                name="Default",
                audit=AuditConfig(
                    base_prob=0.1,
                    high_prob=0.1,
                    false_positive_rate=0.0,
                    false_negative_rate=0.0,
                    penalty_amount=1.0,
                ),
                market=MarketConfig(token_cap=10),
                lab=LabConfig(),
            )

        if kwargs:
            config_dict = config.model_dump()
            for key, value in kwargs.items():
                parts = key.split("__")
                target = config_dict
                for part in parts[:-1]:
                    target = target.setdefault(part, {})
                target[parts[-1]] = value
            config = ScenarioConfig.model_validate(config_dict)

        super().__init__(seed=config.seed)
        self.config = config
        self.n_agents = config.n_agents
        self.running = True

        self.market = SimpleClearingMarket(token_cap=config.market.token_cap)
        if config.market.fixed_price is not None:
            self.market.set_fixed_price(config.market.fixed_price)
        self.auditor = Auditor(config.audit)

        for i in range(self.n_agents):
            gross_value = random.uniform(
                config.lab.gross_value_min, config.lab.gross_value_max
            )
            risk_profile = random.uniform(
                config.lab.risk_profile_min, config.lab.risk_profile_max
            )
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

        from .data_collect import compute_compliance_rate, compute_current_price

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Compliance_Rate": compute_compliance_rate,
                "Price": compute_current_price,
            }
        )

    def step(self) -> None:
        """Execute one step of the simulation."""
        # Reset per-step flags
        for agent in self.agents:
            if isinstance(agent, MesaLab):
                agent.was_audited = False
                agent.detected_cheating = False

        # 1. Trading Phase
        bids = [
            (a.domain_agent.lab_id, a.domain_agent.get_bid())
            for a in self.agents
            if isinstance(a, MesaLab)
        ]

        clearing_price, winning_ids = self.market.allocate(bids)

        winning_set = set(winning_ids)
        for agent in self.agents:
            if isinstance(agent, MesaLab):
                if agent.domain_agent.lab_id in winning_set:
                    agent.domain_agent.has_permit = True
                    agent.wealth -= clearing_price
                else:
                    agent.domain_agent.has_permit = False

        # 2. Compliance Decision
        tpr = 1.0 - self.config.audit.false_negative_rate
        p_s = (
            tpr * self.config.audit.high_prob
            + (1.0 - tpr) * self.config.audit.base_prob
        )
        detection_prob_audit = p_s + (1.0 - p_s) * self.config.audit.backcheck_prob
        p_wb = self.config.audit.whistleblower_prob
        detection_prob = 1.0 - (1.0 - detection_prob_audit) * (1.0 - p_wb)

        for agent in self.agents:
            if isinstance(agent, MesaLab):
                agent.domain_agent.decide_compliance(
                    market_price=clearing_price,
                    penalty=self.config.audit.penalty_amount,
                    detection_prob=detection_prob,
                )

        # 3. Audit Selection
        potential_audits = []
        for agent in self.agents:
            if isinstance(agent, MesaLab):
                is_compliant = agent.domain_agent.is_compliant
                signal = self.auditor.generate_signal(is_compliant)
                if self.auditor.decide_audit(signal):
                    potential_audits.append(agent)

        if self.config.audit.max_audits_per_step is not None:
            if len(potential_audits) > self.config.audit.max_audits_per_step:
                actual_audits = random.sample(
                    potential_audits, self.config.audit.max_audits_per_step
                )
            else:
                actual_audits = potential_audits
        else:
            actual_audits = potential_audits

        # 4. Enforcement
        for agent in actual_audits:
            agent.was_audited = True
            is_compliant = agent.domain_agent.is_compliant
            # Enforce
            if not is_compliant and not agent.domain_agent.has_permit:
                # Caught cheating!
                agent.detected_cheating = True
                agent.wealth -= self.config.audit.penalty_amount

        self.datacollector.collect(self)

    def get_agent_snapshots(self) -> list[dict]:
        """Return a list of dictionaries representing the current state of all agents."""
        snapshots = []
        for agent in self.agents:
            if isinstance(agent, MesaLab):
                snapshots.append(
                    {
                        "ID": agent.domain_agent.lab_id,
                        "Value": agent.domain_agent.gross_value,
                        "Net_Value": agent.domain_agent.gross_value,  # Placeholder
                        "Capability": agent.domain_agent.capability_value,
                        "Allowance": 1.0,  # Placeholder
                        "True_Compute": 1.0,  # Assumption: everyone wants to run 1 unit
                        "Reported_Compute": 1.0
                        if agent.domain_agent.has_permit
                        else (
                            0.0 if agent.domain_agent.is_compliant else 0.0
                        ),  # If compliant+no permit=0. If cheating=0 reported?
                        "Compliant": agent.domain_agent.is_compliant,
                        "Audited": agent.was_audited,
                        "Caught": agent.detected_cheating,
                        "Penalty": self.config.audit.penalty_amount
                        if agent.detected_cheating
                        else 0.0,
                        "Gain": agent.domain_agent.last_gain,
                        "Exp_Penalty": agent.domain_agent.last_expected_penalty,
                        "Wealth": agent.wealth,
                    }
                )
        return snapshots
