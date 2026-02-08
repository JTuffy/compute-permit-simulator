"""Simulation engine - handles simulation execution logic.

This module contains the stateless simulation engine that operates
on the modular state components. It handles model creation, stepping,
and the async play loop.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from compute_permit_sim.schemas import (
    MarketSnapshot,
    SimulationRun,
    StepResult,
)

if TYPE_CHECKING:
    from compute_permit_sim.vis.state.active import ActiveSimulation
    from compute_permit_sim.vis.state.config import UIConfig
    from compute_permit_sim.vis.state.history import SessionHistory

from compute_permit_sim.services.config_manager import load_scenario
from compute_permit_sim.services.metrics import (
    calculate_compliance,
    calculate_wealth_stats,
)
from compute_permit_sim.services.model_wrapper import ComputePermitModel

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Stateful simulation engine with dependency injection.

    This class provides methods to control simulation execution.
    It operates on injected state objects, allowing for better testability.
    """

    def __init__(
        self,
        config: "UIConfig",
        active: "ActiveSimulation",
        history: "SessionHistory",
    ) -> None:
        """Initialize the engine with state dependencies.

        Args:
            config: UI configuration state.
            active: Active simulation state.
            history: Session history state.
        """
        self.config = config
        self.active = active
        self.history = history

    def reset_model(self) -> None:
        """Initialize or reset the Mesa model from current UI config."""
        logger.info("Resetting simulation model")
        scenario_config = self.config.to_scenario_config()

        # Dynamic Seeding: If no seed provided in config, Model will handle it.
        # We capture usage below.

        model = ComputePermitModel(scenario_config)

        # Capture actual seed used by Mesa (for reproducibility)
        # Mesa 3.x stores it in self._seed
        actual_seed = getattr(model, "_seed", None)
        logger.info(f"Model initialized with seed: {actual_seed}")

        # Update unified state in ONE transaction
        self.active.update(
            model=model,
            actual_seed=actual_seed,
            step_count=0,
            compliance_history=[],
            price_history=[],
            agents_df=None,
            is_playing=False,
            current_run_steps=[],
        )

        # Clear selection to show live
        self.history.selected_run.value = None

    def step(self) -> None:
        """Advance the simulation one step."""
        model = self.active.state.value.model
        if not model:
            logger.warning("Attempted to step without a model")
            return

        # Advance step count
        step_num = self.active.state.value.step_count + 1
        logger.debug(f"Starting step {step_num}")

        model.step()

        # Get agent data
        agents = model.get_agent_snapshots()  # Returns list[AgentSnapshot]
        agents_df = pd.DataFrame([a.model_dump() for a in agents])

        # Update time series
        # Update time series
        state = self.active.state.value
        compliance = calculate_compliance(agents)
        new_compliance = state.compliance_history + [compliance]
        new_price = state.price_history + [model.market.current_price]

        # Update wealth history
        compliant_wealth, non_compliant_wealth = calculate_wealth_stats(agents)
        new_wealth_c = state.wealth_history_compliant + [compliant_wealth]
        new_wealth_nc = state.wealth_history_non_compliant + [non_compliant_wealth]

        logger.info(
            f"Step {step_num} complete. Price: {model.market.current_price:.2f}, Compliance: {compliance:.2%}"
        )

        # Store step result
        step_res = StepResult(
            step=step_num,
            market=MarketSnapshot(
                price=model.market.current_price,
                supply=model.market.max_supply,
            ),
            agents=agents,
            audit=[],
        )
        new_run_steps = state.current_run_steps + [step_res]

        # Update unified state
        self.active.update(
            step_count=step_num,
            agents_df=agents_df,
            compliance_history=new_compliance,
            price_history=new_price,
            wealth_history_compliant=new_wealth_c,
            wealth_history_non_compliant=new_wealth_nc,
            current_run_steps=new_run_steps,
        )

    async def play_loop(self) -> None:
        """Async loop for continuous play.

        Uses defensive pattern for Python 3.13 compatibility.
        """
        if not self.active.state.value.is_playing:
            return

        logger.info("Starting play loop")
        try:
            while self.active.state.value.is_playing:
                model = self.active.state.value.model
                config = model.config if model else None

                # Check step limit
                if config and self.active.state.value.step_count >= config.steps:
                    logger.info("Step limit reached in play loop")
                    self.pack_current_run()
                    # Safe to update state here as we are not cancelling
                    self.active.update(is_playing=False)
                    break

                self.step()
                await asyncio.sleep(0.05)

        except asyncio.CancelledError:
            # DO NOT update reactive state here.
            # Just acknowledge and exit.
            logger.debug("Play loop task cancelled gracefully.")
            raise
        except Exception as e:
            logger.error(f"Error in play loop: {e}", exc_info=True)
            self.active.update(is_playing=False)

    def pack_current_run(self) -> None:
        """Finalize the current run and add to history."""
        model = self.active.state.value.model
        if not model:
            return

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        logger.info(f"Packing run {timestamp}")

        # Calculate final metrics
        # Calculate final metrics
        agents = model.get_agent_snapshots()
        final_compliance = calculate_compliance(agents)

        # Ensure config has the ACTUAL seed used
        final_config = self.config.to_scenario_config()
        # Force the captured seed into the config record so it can be restored
        # We need to perform a copy/update since model is frozen
        final_config = final_config.model_copy(
            update={"seed": self.active.state.value.actual_seed}
        )

        # Calculate Regulator Metrics
        total_audits = sum(
            len(step.audit) for step in self.active.state.value.current_run_steps
        )
        # Use simple constant cost for now, or read from config if added later.
        audit_cost_per_unit = model.config.audit.cost
        total_enforcement_cost = total_audits * audit_cost_per_unit

        import hashlib
        import json

        # We need to recreate the exact dict structure used in solara_app.py
        c = final_config
        # Use strongly typed UrlConfig
        from compute_permit_sim.schemas import UrlConfig

        run_state = UrlConfig(
            n_agents=c.n_agents,
            steps=c.steps,
            token_cap=c.market.token_cap,
            seed=c.seed,
            penalty=c.audit.penalty_amount,
            base_prob=c.audit.base_prob,
            high_prob=c.audit.high_prob,
            signal_fpr=c.audit.false_positive_rate,
            signal_tpr=1.0 - c.audit.false_negative_rate,
            backcheck_prob=c.audit.backcheck_prob,
            audit_cost=c.audit.cost,
            ev_min=c.lab.economic_value_min,
            ev_max=c.lab.economic_value_max,
            risk_min=c.lab.risk_profile_min,
            risk_max=c.lab.risk_profile_max,
            cap_min=c.lab.capacity_min,
            cap_max=c.lab.capacity_max,
            vb=c.lab.capability_value,
            cr=c.lab.racing_factor,
            rep=c.lab.reputation_sensitivity,
            audit_coeff=c.lab.audit_coefficient,
        ).model_dump(exclude_none=True)

        # Compute SHA-256 Hash
        json_bytes = json.dumps(run_state, sort_keys=True).encode("utf-8")
        full_hash = hashlib.sha256(json_bytes).hexdigest()
        short_hash = full_hash[:8]

        # Use simpler timestamp for display ID, but store sim_id as short hash
        from compute_permit_sim.schemas import RunMetrics

        run = SimulationRun(
            id=f"run_{timestamp}",
            sim_id=short_hash,
            config=final_config,
            steps=self.active.state.value.current_run_steps.copy(),
            metrics=RunMetrics(
                final_compliance=final_compliance,
                final_price=model.market.current_price,
                total_enforcement_cost=total_enforcement_cost,
                deterrence_success_rate=final_compliance,
            ),
        )

        self.history.add_run(run)

        # Auto-select to show results immediately (reveals slider)
        self.history.select_run(run)

    def load_scenario(self, filename: str) -> None:
        """Load a scenario from a JSON file."""
        logger.info(f"Loading scenario: {filename}")
        try:
            config = load_scenario(filename)
            self.config.from_scenario_config(config)
            self.config.selected_scenario.value = config.name or filename
            self.reset_model()
        except Exception as e:
            logger.error(f"Error loading scenario {filename}: {e}")
            print(f"Error loading scenario {filename}: {e}")

    def restore_config(self, run: SimulationRun) -> None:
        """Restore configuration from a past run."""
        logger.info(f"Restoring config from run {run.id}")
        c = run.config

        # Apply Top Level
        self.config.n_agents.value = c.n_agents
        self.config.steps.value = c.steps
        self.config.token_cap.value = int(c.market.token_cap)

        # Audit
        self.config.base_prob.value = c.audit.base_prob
        self.config.high_prob.value = c.audit.high_prob
        self.config.penalty.value = c.audit.penalty_amount

        # Lab
        self.config.economic_value_min.value = c.lab.economic_value_min
        self.config.economic_value_max.value = c.lab.economic_value_max
        self.config.risk_profile_min.value = c.lab.risk_profile_min
        self.config.risk_profile_max.value = c.lab.risk_profile_max
        self.config.capacity_min.value = getattr(c.lab, "capacity_min", 1.0)
        self.config.capacity_max.value = getattr(c.lab, "capacity_max", 2.0)
        self.config.capability_value.value = getattr(c.lab, "capability_value", 0.0)
        self.config.racing_factor.value = getattr(c.lab, "racing_factor", 1.0)
        self.config.reputation_sensitivity.value = getattr(
            c.lab, "reputation_sensitivity", 0.0
        )
        self.config.audit_coefficient.value = getattr(c.lab, "audit_coefficient", 1.0)

        # Restore SEED
        self.config.seed.value = c.seed
        logger.info(f"Restored seed: {c.seed}")

        self.config.selected_scenario.value = "Restored"

    def save_run(self, name_prefix="run") -> str | None:
        """Persist the structured simulation run to a JSON file."""
        model = self.active.state.value.model
        if not model:
            return None

        run_to_save = self.history.selected_run.value
        if not run_to_save:
            timestamp = time.strftime("%Y%m%d_%H%M%S")

            # Ensure config has seed
            final_config = self.config.to_scenario_config()
            final_config = final_config.model_copy(
                update={"seed": self.active.state.value.actual_seed}
            )

            run_to_save = SimulationRun(
                id=f"{timestamp}_current",
                config=final_config,
                steps=self.active.state.value.current_run_steps,
                metrics={},
            )

        run_dir = Path("runs") / run_to_save.id
        run_dir.mkdir(parents=True, exist_ok=True)

        filepath = run_dir / "full_run.json"
        with open(filepath, "w") as f:
            f.write(run_to_save.model_dump_json(indent=2))

        logger.info(f"Saved run to {filepath}")
        return str(run_dir)
