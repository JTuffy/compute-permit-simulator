"""Simulation engine - handles simulation execution logic.

This module contains the stateless simulation engine that operates
on the modular state components. It handles model creation, stepping,
and the async play loop.
"""

import asyncio
import logging
import time
from pathlib import Path

import pandas as pd

from compute_permit_sim.schemas import (
    SimulationRun,
    StepResult,
)
from compute_permit_sim.services.config_manager import load_scenario
from compute_permit_sim.services.model_wrapper import ComputePermitModel
from compute_permit_sim.vis.state.active import ActiveSimulation, active_sim
from compute_permit_sim.vis.state.config import UIConfig, ui_config
from compute_permit_sim.vis.state.history import SessionHistory, session_history

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Stateful simulation engine with dependency injection.

    This class provides methods to control simulation execution.
    It operates on injected state objects, allowing for better testability.
    """

    def __init__(
        self,
        config: UIConfig,
        active: ActiveSimulation,
        history: SessionHistory,
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

        model = ComputePermitModel(scenario_config)
        self.active.model.value = model

        # Capture actua seed used by Mesa (for reproducibility)
        # Mesa 3.x stores it in self._seed
        actual_seed = getattr(model, "_seed", None)
        self.active.actual_seed.value = actual_seed
        logger.info(f"Model initialized with seed: {actual_seed}")

        self.active.step_count.value = 0
        self.active.compliance_history.value = []
        self.active.price_history.value = []
        self.active.agents_df.value = None
        self.active.is_playing.value = False
        self.active.current_run_steps = []

        # Clear selection to show live
        self.history.selected_run.value = None

    def step(self) -> None:
        """Advance the simulation one step."""
        model = self.active.model.value
        if not model:
            logger.warning("Attempted to step without a model")
            return

        step_num = self.active.step_count.value + 1
        logger.debug(f"Starting step {step_num}")

        model.step()
        self.active.step_count.value = step_num

        # Get agent data
        agents = model.get_agent_snapshots()  # Returns list[dict] with snake_case keys
        self.active.agents_df.value = pd.DataFrame(agents)

        # Update time series
        # Ensure we access the correct key "is_compliant"
        compliance = (
            sum(a.get("is_compliant", False) for a in agents) / len(agents)
            if agents
            else 0
        )
        self.active.compliance_history.value = self.active.compliance_history.value + [
            compliance
        ]
        self.active.price_history.value = self.active.price_history.value + [
            model.market.current_price
        ]

        logger.info(
            f"Step {step_num} complete. Price: {model.market.current_price:.2f}, Compliance: {compliance:.2%}"
        )

        # Store step result using Pydantic schema
        step_res = StepResult(
            step=self.active.step_count.value,
            market={
                "price": model.market.current_price,
                "supply": model.market.max_supply,
            },
            agents=agents,  # StepResult agents is list[AgentSnapshot]
            audit=[],
        )
        self.active.current_run_steps.append(step_res)

    async def play_loop(self) -> None:
        """Async loop for continuous play.

        Uses defensive pattern for Python 3.13 compatibility.
        """
        if not self.active.is_playing.value:
            return

        logger.info("Starting play loop")
        try:
            while self.active.is_playing.value:
                model = self.active.model.value
                config = model.config if model else None

                # Check step limit
                if config and self.active.step_count.value >= config.steps:
                    logger.info("Step limit reached in play loop")
                    self.pack_current_run()
                    break

                self.step()
                await asyncio.sleep(0.05)

        except asyncio.CancelledError:
            logger.info("Play loop cancelled")
            pass
        except Exception as e:
            logger.error(f"Error in play loop: {e}", exc_info=True)
            self.active.is_playing.set(False)
        finally:
            self.active.is_playing.set(False)

    def pack_current_run(self) -> None:
        """Finalize the current run and add to history."""
        model = self.active.model.value
        if not model:
            return

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        logger.info(f"Packing run {timestamp}")

        # Calculate final metrics
        agents = model.get_agent_snapshots()
        final_compliance = (
            sum(a.get("is_compliant", False) for a in agents) / len(agents)
            if agents
            else 0
        )

        # Ensure config has the ACTUAL seed used
        final_config = self.config.to_scenario_config()
        # Force the captured seed into the config record so it can be restored
        # We need to perform a copy/update since model is frozen
        final_config = final_config.model_copy(
            update={"seed": self.active.actual_seed.value}
        )

        run = SimulationRun(
            id=f"run_{timestamp}",
            config=final_config,
            steps=self.active.current_run_steps.copy(),
            metrics={
                "final_compliance": final_compliance,
                "final_price": model.market.current_price,
            },
        )

        self.history.add_run(run)

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
        model = self.active.model.value
        if not model:
            return None

        run_to_save = self.history.selected_run.value
        if not run_to_save:
            timestamp = time.strftime("%Y%m%d_%H%M%S")

            # Ensure config has seed
            final_config = self.config.to_scenario_config()
            final_config = final_config.model_copy(
                update={"seed": self.active.actual_seed.value}
            )

            run_to_save = SimulationRun(
                id=f"{timestamp}_current",
                config=final_config,
                steps=self.active.current_run_steps,
                metrics={},
            )

        run_dir = Path("runs") / run_to_save.id
        run_dir.mkdir(parents=True, exist_ok=True)

        filepath = run_dir / "full_run.json"
        with open(filepath, "w") as f:
            f.write(run_to_save.model_dump_json(indent=2))

        logger.info(f"Saved run to {filepath}")
        return str(run_dir)


# Singleton instance with default state modules injected
engine = SimulationEngine(ui_config, active_sim, session_history)
