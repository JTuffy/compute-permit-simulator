"""Mesa model integration for the Compute Permit Simulator."""

import random

import mesa

try:
    import numpy as np
except ImportError:
    np = None

from typing import TYPE_CHECKING

from compute_permit_sim.core.constants import (
    DEFAULT_AUDIT_BASE_PROB,
    DEFAULT_AUDIT_FALSE_NEG_RATE,
    DEFAULT_AUDIT_FALSE_POS_RATE,
    DEFAULT_AUDIT_HIGH_PROB,
    DEFAULT_AUDIT_PENALTY_AMOUNT,
    DEFAULT_MARKET_TOKEN_CAP,
)
from compute_permit_sim.services.data_collect import (
    compute_compliance_rate,
    compute_current_price,
)

from ..core.agents import Lab
from ..core.enforcement import Auditor
from ..core.market import SimpleClearingMarket
from ..schemas import AuditConfig, LabConfig, MarketConfig, ScenarioConfig

if TYPE_CHECKING:
    from ..schemas import AgentSnapshot


class MesaLab(mesa.Agent):
    """Mesa wrapper for the Lab domain logic.

    Attributes:
        unique_id: Unique integer identifier for the agent.
        domain_agent: The underlying Lab domain object handling compliance logic.
        wealth: Cumulative wealth (net gains minus penalties and fees).
        last_audit_status: Summary of the most recent audit results.
    """

    def __init__(
        self,
        unique_id: int,
        model: mesa.Model,
        config: "LabConfig",
        economic_value: float,
        risk_profile: float,
        capacity: float,
    ) -> None:
        """Initialize a Mesa-managed Lab agent.

        Args:
            unique_id: Unique identifier.
            model: The Mesa model instance.
            config: Shared lab configuration.
            economic_value: Baseline value (v_i) of training compute.
            risk_profile: Deterrence sensitivity.
            capacity: Max compute capacity.
        """
        super().__init__(model)
        self.unique_id = unique_id
        self.domain_agent = Lab(
            unique_id,
            config,
            economic_value,
            risk_profile,
            capacity,
        )
        self.wealth: float = 0.0
        self.last_step_profit: float = 0.0
        # Tracking for visualization
        self.last_audit_status = {"audited": False, "caught": False, "penalty": 0.0}

    def step(self) -> None:
        """Execute one step of the agent.

        Note: Model controls phase order explicitly.
        step() might be empty if Model orchestrates phases.
        We let Model orchestrate phases (trade, run, etc.) to ensure strict order.
        """
        pass


class ComputePermitModel(mesa.Model):
    """The central Mesa model.

    Architecture Reference:
        source/Week_2_simulation_architecture_josh.md Section 1 "High-Lift Components"
        - Orchestrates "Actor Behavior" and "Permit Market" phases.
    """

    def __init__(self, config: ScenarioConfig = None, **kwargs) -> None:
        """Initialize the model.

        Args:
            config: Full scenario configuration.
            **kwargs: Overrides for configuration parameters
                (for Mesa BatchRunner).
        """
        if config is None:
            # Create default config if none provided
            config = ScenarioConfig(
                name="Default",
                audit=AuditConfig(
                    base_prob=DEFAULT_AUDIT_BASE_PROB,
                    high_prob=DEFAULT_AUDIT_HIGH_PROB,
                    false_positive_rate=DEFAULT_AUDIT_FALSE_POS_RATE,
                    false_negative_rate=DEFAULT_AUDIT_FALSE_NEG_RATE,
                    penalty_amount=DEFAULT_AUDIT_PENALTY_AMOUNT,
                ),
                market=MarketConfig(token_cap=DEFAULT_MARKET_TOKEN_CAP),
                lab=LabConfig(),
            )

        # Apply kwargs overrides (nested update support)
        if kwargs:
            # Convert to dict first
            config_dict = config.model_dump()

            for key, value in kwargs.items():
                parts = key.split("__")
                target = config_dict
                for part in parts[:-1]:
                    target = target.setdefault(part, {})
                target[parts[-1]] = value

            # Re-validate to ensure nested objects are recreated:
            config = ScenarioConfig.model_validate(config_dict)

        super().__init__(seed=config.seed)
        self.config = config
        self.n_agents = config.n_agents

        # --- SEEDING FOR DETERMINISM ---
        # User wants "Seed as Identity". We must seed global RNGs to ensure
        # components using 'random' (like Auditor) or 'numpy' are deterministic.

        # Mesa has already set self._seed (either from config.seed or auto-generated)
        current_seed = getattr(self, "_seed", config.seed)

        # If Mesa didn't set _seed (older versions?), fallback to config or random
        if current_seed is None:
            current_seed = random.randint(0, 1000000)
            self._seed = current_seed

        # Apply to GLOBAL generic RNGs
        random.seed(current_seed)

        # Use top-level numpy if available
        if np is not None:
            np.random.seed(current_seed)

        self.running = True

        # Initialize Market and Auditor
        self.market = SimpleClearingMarket(token_cap=config.market.token_cap)
        if config.market.fixed_price is not None:
            self.market.set_fixed_price(config.market.fixed_price)
        self.auditor = Auditor(config.audit)

        # Initialize Agents (IDs start at 1)
        for i in range(self.n_agents):
            economic_value = self.random.uniform(
                config.lab.economic_value_min, config.lab.economic_value_max
            )
            risk_profile = self.random.uniform(
                config.lab.risk_profile_min, config.lab.risk_profile_max
            )
            capacity = self.random.uniform(
                config.lab.capacity_min, config.lab.capacity_max
            )
            # Pass all extended parameters to the agent
            MesaLab(
                i + 1,  # Start IDs at 1
                self,
                config=config.lab,
                economic_value=economic_value,
                risk_profile=risk_profile,
                capacity=capacity,
            )
            # Agent is automatically added to self.agents in Mesa 3.x

        # Data Collection
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Compliance_Rate": compute_compliance_rate,
                "Price": compute_current_price,
            }
        )

    def step(self) -> None:
        """Execute one step of the simulation (matches Game Loop)."""
        # Reset per-step profit tracking
        for agent in self.agents:
            if isinstance(agent, MesaLab):
                agent.last_step_profit = 0.0

        # 1. Trading Phase
        # Collect bids (valuations) from all agents
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
                    agent.last_step_profit -= clearing_price
                else:
                    agent.domain_agent.has_permit = False

        # 2. Choice Phase (Run / Compliance)
        # TPR = 1 - FNR (beta)
        tpr = 1.0 - self.config.audit.false_negative_rate
        p_s = (
            tpr * self.config.audit.high_prob
            + (1.0 - tpr) * self.config.audit.base_prob
        )
        detection_prob_audit = p_s + (1.0 - p_s) * self.config.audit.backcheck_prob

        # Combine with whistleblower prob: p_eff = 1 - (1-p_audit)(1-p_wb)
        p_wb = self.config.audit.whistleblower_prob
        detection_prob = 1.0 - (1.0 - detection_prob_audit) * (1.0 - p_wb)

        for agent in self.agents:
            if isinstance(agent, MesaLab):
                agent.domain_agent.decide_compliance(
                    market_price=clearing_price,
                    penalty=self.config.audit.penalty_amount,
                    detection_prob=detection_prob,
                    # cost ignored for MVP or folded into net value
                )

        # 3. Signal Phase & 4. Enforcement Phase
        potential_audits = []

        for agent in self.agents:
            if isinstance(agent, MesaLab):
                is_compliant = agent.domain_agent.is_compliant
                signal = self.auditor.generate_signal(is_compliant)
                # Check if auditor WANTS to audit (based on signal policy)
                should_audit = self.auditor.decide_audit(signal)

                if should_audit:
                    potential_audits.append(agent)

        # Apply Audit Capacity Constraint
        if self.config.audit.max_audits_per_step is not None:
            if len(potential_audits) > self.config.audit.max_audits_per_step:
                # Randomly select subset to audit (limited resources)
                actual_audits = self.random.sample(
                    potential_audits, self.config.audit.max_audits_per_step
                )
            else:
                actual_audits = potential_audits
        else:
            actual_audits = potential_audits

        # Execute Audits
        for agent in actual_audits:
            is_compliant = agent.domain_agent.is_compliant
            # Reset audit status
            agent.last_audit_status = {"audited": True, "caught": False, "penalty": 0.0}
            # Enforce
            if not is_compliant and not agent.domain_agent.has_permit:
                # Caught cheating!
                agent.wealth -= self.config.audit.penalty_amount
                agent.last_step_profit -= self.config.audit.penalty_amount
                agent.last_audit_status["caught"] = True
                agent.last_audit_status["penalty"] = self.config.audit.penalty_amount

        # Reset audit status for non-audited agents
        for agent in self.agents:
            if isinstance(agent, MesaLab) and agent not in actual_audits:
                agent.last_audit_status = {
                    "audited": False,
                    "caught": False,
                    "penalty": 0.0,
                }

        # 5. Value Realization Phase
        # Agents who run compute (legally with permit, or illegally) get value
        for agent in self.agents:
            if isinstance(agent, MesaLab):
                d = agent.domain_agent
                # Agents with permits ran legally - already paid permit price
                if d.has_permit:
                    agent.wealth += d.economic_value  # They get the value of the run
                    agent.last_step_profit += d.economic_value
                # Non-compliant agents without permits ran illegally
                elif not d.is_compliant:
                    agent.wealth += d.economic_value  # They get the value (cheating)
                    agent.last_step_profit += d.economic_value
                # Compliant agents without permits didn't run - no value gained
                # (they chose not to run because they couldn't afford permit)

        self.datacollector.collect(self)

    def get_agent_snapshots(self) -> list["AgentSnapshot"]:
        """Capture standard view of agent state for UI/Data collection.

        Returns:
            List of AgentSnapshot objects containing agent metrics.
        """
        from ..schemas import AgentSnapshot

        snapshots = []
        for agent in self.agents:
            if isinstance(agent, MesaLab):
                d = agent.domain_agent

                # Determine what compute was actually used this step
                did_run = d.has_permit or not d.is_compliant
                true_compute = d.capacity if did_run else 0.0

                # Reported compute logic
                if d.has_permit:
                    reported_compute = d.capacity
                elif d.is_compliant:
                    reported_compute = 0.0
                else:
                    reported_compute = 0.0

                snapshots.append(
                    AgentSnapshot(
                        id=d.lab_id,
                        capacity=round(d.capacity, 2),
                        has_permit=d.has_permit,
                        used_compute=round(true_compute, 2),
                        reported_compute=round(reported_compute, 2),
                        is_compliant=d.is_compliant,
                        was_audited=agent.last_audit_status["audited"],
                        was_caught=agent.last_audit_status["caught"],
                        penalty_amount=agent.last_audit_status["penalty"],
                        revenue=round(d.economic_value, 2),
                        economic_value=round(d.economic_value, 2),
                        risk_profile=round(d.risk_profile, 2),
                        step_profit=round(agent.last_step_profit, 2),
                        wealth=round(agent.wealth, 2),
                    )
                )
        return snapshots
