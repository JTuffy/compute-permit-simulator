"""Mesa model integration for the Compute Permit Simulator."""

from typing import TYPE_CHECKING

import mesa

from compute_permit_sim.schemas.defaults import (
    DEFAULT_AUDIT_BASE_PROB,
    DEFAULT_AUDIT_FALSE_NEG_RATE,
    DEFAULT_AUDIT_FALSE_POS_RATE,
    DEFAULT_AUDIT_HIGH_PROB,
    DEFAULT_AUDIT_PENALTY_AMOUNT,
    DEFAULT_MARKET_TOKEN_CAP,
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
        firm_revenue: float = 0.0,
        planned_training_flops: float = 0.0,
    ) -> None:
        """Initialize a Mesa-managed Lab agent.

        Args:
            unique_id: Unique identifier.
            model: The Mesa model instance.
            config: Shared lab configuration.
            economic_value: Baseline value (v_i) of training compute.
            risk_profile: Deterrence sensitivity.
            capacity: Max compute capacity.
            firm_revenue: Annual revenue/turnover (M$) for penalty calculation.
            planned_training_flops: Planned training run size (FLOP).
        """
        super().__init__(model)
        self.unique_id = unique_id
        self.domain_agent = Lab(
            unique_id,
            config,
            economic_value,
            risk_profile,
            capacity,
            firm_revenue=firm_revenue,
            planned_training_flops=planned_training_flops,
        )
        self.wealth: float = 0.0
        self.last_step_profit: float = 0.0
        # Tracking for visualization
        self.last_audit_status = {
            "audited": False,
            "caught": False,
            "penalty": 0.0,
            "collateral_seized": False,
        }

    def step(self) -> None:
        """Execute one step of the agent.

        Note: Model controls phase order explicitly.
        step() might be empty if Model orchestrates phases.
        We let Model orchestrate phases (trade, run, etc.) to ensure strict order.
        """
        pass


class ComputePermitModel(mesa.Model):
    """The central Mesa model.

    Orchestrates "Actor Behavior" and "Permit Market" phases.
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
        self.running = True

        # Initialize Market and Auditor
        # Pass self.random (Mesa's seeded RNG) to Auditor for reproducibility
        self.market = SimpleClearingMarket(token_cap=config.market.token_cap)
        if config.market.fixed_price is not None:
            self.market.set_fixed_price(config.market.fixed_price)
        self.auditor = Auditor(config.audit, rng=self.random)

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
            firm_revenue = self.random.uniform(
                config.lab.firm_revenue_min, config.lab.firm_revenue_max
            )
            planned_training_flops = self.random.uniform(
                config.lab.training_flops_min, config.lab.training_flops_max
            )
            # Pass all extended parameters to the agent
            MesaLab(
                i + 1,  # Start IDs at 1
                self,
                config=config.lab,
                economic_value=economic_value,
                risk_profile=risk_profile,
                capacity=capacity,
                firm_revenue=firm_revenue,
                planned_training_flops=planned_training_flops,
            )
            # Agent is automatically added to self.agents in Mesa 3.x

        # Data Collection
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Compliance_Rate": lambda m: (
                    sum(
                        1
                        for a in m.agents
                        if isinstance(a, MesaLab) and a.domain_agent.is_compliant
                    )
                    / max(
                        1,
                        sum(1 for a in m.agents if isinstance(a, MesaLab)),
                    )
                ),
                "Price": lambda m: m.market.current_price,
            }
        )

    def step(self) -> None:
        """Execute one step of the simulation (delegates to core game loop)."""
        from compute_permit_sim.core.game_loop import execute_step

        # Extract domain objects
        mesa_labs = [a for a in self.agents if isinstance(a, MesaLab)]
        domain_labs = [a.domain_agent for a in mesa_labs]

        # Run pure game loop
        result = execute_step(
            labs=domain_labs,
            market=self.market,
            auditor=self.auditor,
            config=self.config,
            rng=self.random,
        )

        # Apply results to Mesa wrappers
        for agent in mesa_labs:
            ao = result.agent_outcomes[agent.domain_agent.lab_id]
            agent.wealth += ao.wealth_delta
            agent.last_step_profit = ao.wealth_delta
            agent.last_audit_status = {
                "audited": ao.audited,
                "caught": ao.caught,
                "penalty": ao.penalty,
                "collateral_seized": ao.collateral_seized,
            }

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
