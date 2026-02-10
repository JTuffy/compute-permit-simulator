"""Mesa model integration for the Compute Permit Simulator."""

from typing import TYPE_CHECKING

import mesa

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

        # 0. Collateral Phase — labs post refundable collateral
        # Ref: Christoph (2026) §2.6 step 2: "Participants post collateral K"
        collateral_k = self.config.collateral_amount
        if collateral_k > 0:
            for agent in self.agents:
                if isinstance(agent, MesaLab):
                    agent.domain_agent.collateral_posted = collateral_k
                    agent.wealth -= collateral_k
                    agent.last_step_profit -= collateral_k

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
        # Compute detection probability for deterrence calculation
        # Labs estimate their detection risk based on expected signal strength
        flop_threshold = self.config.flop_threshold
        for agent in self.agents:
            if isinstance(agent, MesaLab):
                d = agent.domain_agent
                # Estimate signal strength if they were to cheat
                # (used for deterrence calculation)
                hypothetical_usage = d.planned_training_flops
                expected_signal = self.auditor.compute_signal_strength(
                    used_compute=hypothetical_usage,
                    flop_threshold=flop_threshold,
                    is_compliant=False,  # hypothetical cheating scenario
                )
                # Compute effective detection probability
                # Uses current_audit_coefficient (may be escalated via dynamic factors)
                detection_prob_audit = self.auditor.compute_effective_detection(
                    audit_coefficient=d.current_audit_coefficient,
                    signal_strength=expected_signal,
                )
                # Combine with whistleblower prob: p_eff = 1 - (1-p_audit)(1-p_wb)
                p_wb = self.config.audit.whistleblower_prob
                detection_prob = 1.0 - (1.0 - detection_prob_audit) * (1.0 - p_wb)

                # Compute firm-specific penalty for deterrence calculation
                firm_penalty = self.auditor.compute_penalty_amount(
                    firm_value=d.firm_revenue
                )
                d.decide_compliance(
                    market_price=clearing_price,
                    penalty=firm_penalty,
                    detection_prob=detection_prob,
                )

        # 3. Signal Phase & 4. Enforcement Phase
        potential_audits = []

        for agent in self.agents:
            if isinstance(agent, MesaLab):
                d = agent.domain_agent
                is_compliant = d.is_compliant

                # Determine actual compute used this step
                did_run = d.has_permit or not is_compliant
                used_compute = d.planned_training_flops if did_run else 0.0

                # Generate signal based on usage relative to threshold
                signal_strength = self.auditor.generate_signal(
                    used_compute=used_compute,
                    flop_threshold=flop_threshold,
                    is_compliant=is_compliant,
                )

                # Decide whether to audit based on signal strength
                should_audit = self.auditor.decide_audit(signal_strength)

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

        # Execute Audits - use FPR/FNR to determine if violation is found
        for agent in actual_audits:
            d = agent.domain_agent
            is_compliant = d.is_compliant
            has_permit = d.has_permit

            # Audit status: audited but outcome depends on FPR/FNR
            agent.last_audit_status = {
                "audited": True,
                "caught": False,
                "penalty": 0.0,
                "collateral_seized": False,
            }

            # Determine if audit finds a violation
            # For firms with permits, they're effectively "compliant" for audit purposes
            effective_compliant = is_compliant or has_permit
            violation_found = self.auditor.audit_finds_violation(effective_compliant)

            if violation_found and not has_permit:
                # Caught! (true positive for non-compliant, or false positive for compliant)
                # Pass firm_revenue for flexible penalty: max(fixed, pct × revenue), capped
                penalty = self.auditor.apply_penalty(
                    violation_found=True, firm_value=d.firm_revenue
                )
                agent.wealth -= penalty
                agent.last_step_profit -= penalty
                agent.last_audit_status["caught"] = True
                agent.last_audit_status["penalty"] = penalty

                # Seize collateral on verified violation
                # Ref: Christoph (2026) §2.6 step 8: "collateral seized"
                if d.collateral_posted > 0:
                    agent.last_audit_status["collateral_seized"] = True
                    # Collateral already deducted in phase 0; don't refund it
                    d.collateral_posted = 0.0

                # Dynamic factors: escalate reputation and audit coefficient
                d.on_audit_failure(
                    audit_escalation=self.config.audit.audit_escalation,
                )

        # Reset audit status for non-audited agents
        for agent in self.agents:
            if isinstance(agent, MesaLab) and agent not in actual_audits:
                agent.last_audit_status = {
                    "audited": False,
                    "caught": False,
                    "penalty": 0.0,
                    "collateral_seized": False,
                }

        # Refund collateral for agents not caught
        # Ref: Christoph (2026) §2.6 step 9: "Non-violators receive collateral refunds"
        if collateral_k > 0:
            for agent in self.agents:
                if isinstance(agent, MesaLab):
                    d = agent.domain_agent
                    if d.collateral_posted > 0:
                        # Not seized — refund
                        agent.wealth += d.collateral_posted
                        agent.last_step_profit += d.collateral_posted
                        d.collateral_posted = 0.0

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

        # 6. Dynamic Factor Updates (end-of-step)
        # Decay audit coefficients toward base for all labs
        audit_decay = self.config.audit.audit_decay_rate
        for agent in self.agents:
            if isinstance(agent, MesaLab):
                agent.domain_agent.decay_audit_coefficient(audit_decay)

        # Update racing factors based on relative capability position
        capabilities = [
            a.domain_agent.cumulative_capability
            for a in self.agents
            if isinstance(a, MesaLab)
        ]
        if capabilities:
            mean_cap = sum(capabilities) / len(capabilities)
            for agent in self.agents:
                if isinstance(agent, MesaLab):
                    agent.domain_agent.update_racing_factor(mean_cap)

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
