"""Simulation engine - handles simulation execution logic.

This module contains the stateless simulation engine that operates
on the modular state components. It handles model creation, stepping,
and the async play loop.
"""

import asyncio
import logging
import random
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from compute_permit_sim.schemas import (
    MarketSnapshot,
    RunMetrics,
    SimulationRun,
    StepResult,
)

if TYPE_CHECKING:
    from compute_permit_sim.vis.state.active import ActiveSimulation
    from compute_permit_sim.vis.state.config import UIConfig
    from compute_permit_sim.vis.state.history import SessionHistory

from compute_permit_sim.services.config_manager import load_scenario
from compute_permit_sim.services.mesa_model import ComputePermitModel
from compute_permit_sim.services.metrics import (
    calculate_compliance,
    calculate_wealth_stats,
)

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

    def start_run(self) -> None:
        """Start a fresh simulation run from the current UI configuration."""
        # --- Resolve seed ---
        ui_seed = self.config.seed.value
        run_seed = ui_seed if ui_seed is not None else random.randint(0, 2**31 - 1)

        # Build config from CURRENT UI values
        scenario_config = self.config.to_scenario_config()
        # Inject the resolved seed (model_copy because ScenarioConfig is frozen)
        scenario_config = scenario_config.model_copy(update={"seed": run_seed})

        logger.info(
            f"Starting new run with seed={run_seed} (user-provided={ui_seed is not None})"
        )

        model = ComputePermitModel(scenario_config)

        # Capture actual seed written by Mesa (for reproducibility record)
        actual_seed = getattr(model, "_seed", run_seed)
        logger.info(f"Model initialized with seed: {actual_seed}")

        # Reset all active state and start playing in ONE transaction
        self.active.update(
            model=model,
            actual_seed=actual_seed,
            step_count=0,
            compliance_history=[],
            price_history=[],
            wealth_history_compliant=[],
            wealth_history_non_compliant=[],
            agents_df=None,
            is_playing=True,
            current_run_steps=[],
        )

        # Clear history selection to show live view
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
        """Async loop that runs all steps until the step limit is reached.

        Triggered by SimulationController when is_playing transitions to True.
        Uses defensive pattern for Python 3.13 compatibility.
        """
        if not self.active.state.value.is_playing:
            return

        logger.info("Play loop started")
        try:
            while self.active.state.value.is_playing:
                model = self.active.state.value.model
                if not model:
                    break

                # Check step limit
                if self.active.state.value.step_count >= model.config.steps:
                    logger.info("Step limit reached — packing run")
                    self.pack_current_run()
                    self.active.update(is_playing=False)
                    break

                self.step()
                await asyncio.sleep(0.05)

        except asyncio.CancelledError:
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

        import base64
        import hashlib
        import json

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        logger.info(f"Packing run {timestamp}")

        # Calculate final metrics
        agents = model.get_agent_snapshots()
        final_compliance = calculate_compliance(agents)

        # Build final config with the ACTUAL seed used (not the UI field)
        final_config = self.config.to_scenario_config()
        final_config = final_config.model_copy(
            update={"seed": self.active.state.value.actual_seed}
        )

        # Regulator metrics
        total_audits = sum(
            len(step.audit) for step in self.active.state.value.current_run_steps
        )
        total_enforcement_cost = total_audits * model.config.audit.cost

        # Build compact config for hashing and shareable URL
        # We use exclude_defaults=True to keep the URL short and avoid maintaining a separate UrlConfig DTO.
        run_state = final_config.model_dump(exclude_defaults=True, exclude_none=True)

        # sim_id: short SHA-256 hash for display label
        json_bytes = json.dumps(run_state, sort_keys=True).encode("utf-8")
        short_hash = hashlib.sha256(json_bytes).hexdigest()[:8]

        # url_id: base64-encoded JSON for shareable ?id=... URL
        url_id = base64.b64encode(json.dumps(run_state).encode("utf-8")).decode("utf-8")

        run = SimulationRun(
            id=f"run_{timestamp}",
            sim_id=short_hash,
            url_id=url_id,
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
        """Load a scenario from a JSON file into the UI config.

        This updates UI reactive state only.  The user must click Play
        to actually start a run with the loaded parameters.
        """
        logger.info(f"Loading scenario: {filename}")
        try:
            config = load_scenario(filename)
            self.config.from_scenario_config(config)
            self.config.selected_scenario.value = config.name or filename
        except Exception as e:
            logger.error(f"Error loading scenario {filename}: {e}")
            print(f"Error loading scenario {filename}: {e}")

    def restore_config(self, run: SimulationRun) -> None:
        """Restore configuration from a past run."""
        logger.info(f"Restoring config from run {run.id}")
        self.config.from_scenario_config(run.config)
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
