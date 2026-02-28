"""Mesa model integration for the Compute Permit Simulator."""

from typing import TYPE_CHECKING

import mesa

from ..core.agents import Lab
from ..core.enforcement import Auditor
from ..core.market import SimpleClearingMarket
from ..schemas import LabConfig, ScenarioConfig

if TYPE_CHECKING:
    from ..schemas import AgentSnapshot


class MesaLab(mesa.Agent):
    """Mesa wrapper for the Lab domain logic."""

    def __init__(
        self,
        unique_id: int,
        model: mesa.Model,
        config: "LabConfig",
        economic_value: float,
        risk_profile: float,
        planned_training_flops: float = 0.0,
        penalty_amount: float = 0.0,
    ) -> None:
        super().__init__(model)
        self.unique_id = unique_id
        self.domain_agent = Lab(
            unique_id,
            config,
            economic_value,
            risk_profile,
            planned_training_flops=planned_training_flops,
            penalty_amount=penalty_amount,
        )
        self.last_audit_status = {
            "audited": False,
            "caught": False,
            "penalty": 0.0,
            "collateral_seized": False,
            "ran": False,
        }

    def step(self) -> None:
        pass


class ComputePermitModel(mesa.Model):
    """The central Mesa model.

    Orchestrates "Actor Behavior" and "Permit Market" phases.
    """

    def __init__(self, config: ScenarioConfig | None = None, **kwargs) -> None:
        if config is None:
            config = ScenarioConfig()

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
        self.running = True

        self.market = SimpleClearingMarket(permit_cap=config.market.permit_cap)
        if config.market.fixed_price is not None:
            self.market.set_fixed_price(config.market.fixed_price)
        self.auditor = Auditor(config.audit, rng=self.random)

        for i in range(config.n_agents):
            economic_value = self.random.uniform(
                config.lab.economic_value_min, config.lab.economic_value_max
            )
            risk_profile = self.random.uniform(
                config.lab.risk_profile_min, config.lab.risk_profile_max
            )
            planned_training_flops = self.random.uniform(
                config.lab.compute_capacity_min, config.lab.compute_capacity_max
            )
            MesaLab(
                i + 1,
                self,
                config=config.lab,
                economic_value=economic_value,
                risk_profile=risk_profile,
                planned_training_flops=planned_training_flops,
                penalty_amount=config.audit.penalty_amount,
            )

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

        mesa_labs = [a for a in self.agents if isinstance(a, MesaLab)]
        domain_labs = [a.domain_agent for a in mesa_labs]

        result = execute_step(
            labs=domain_labs,
            market=self.market,
            auditor=self.auditor,
            config=self.config,
            rng=self.random,
        )

        for agent in mesa_labs:
            ao = result.agent_outcomes[agent.domain_agent.lab_id]
            agent.last_audit_status = {
                "audited": ao.audited,
                "caught": ao.caught,
                "penalty": ao.penalty,
                "collateral_seized": ao.collateral_seized,
                "ran": ao.ran,
            }

        self.datacollector.collect(self)

    def get_agent_snapshots(self) -> list["AgentSnapshot"]:
        """Capture standard view of agent state for UI/data collection."""
        from ..schemas import AgentSnapshot

        flops_per_permit = self.config.market.flops_per_permit
        snapshots = []
        for agent in self.agents:
            if isinstance(agent, MesaLab):
                d = agent.domain_agent
                ran = agent.last_audit_status["ran"]

                used_training_flops = d.planned_training_flops if ran else 0.0

                if flops_per_permit is not None:
                    reported_training_flops = d.permits_held * flops_per_permit
                elif d.has_permit:
                    reported_training_flops = d.planned_training_flops
                else:
                    reported_training_flops = 0.0

                snapshots.append(
                    AgentSnapshot(
                        id=d.lab_id,
                        compute_capacity=d.planned_training_flops,
                        planned_training_flops=d.planned_training_flops,
                        used_training_flops=used_training_flops,
                        reported_training_flops=reported_training_flops,
                        has_permit=d.has_permit,
                        is_compliant=d.is_compliant,
                        was_audited=agent.last_audit_status["audited"],
                        was_caught=agent.last_audit_status["caught"],
                        penalty_amount=agent.last_audit_status["penalty"],
                        economic_value=d.economic_value,
                        risk_profile=d.risk_profile,
                    )
                )
        return snapshots
