"""Simulation engine — headless background runner for basic single-scenario runs.

Uses ``basic_run`` (a ``RunState[SimulationRun]`` reactive) as its single
output signal.  Page-level state machine in ``vis/page.py`` reads this reactive
to drive the right-pane display.

Phases:
    idle    → no run yet
    running → background thread active; right pane shows spinner
    ready   → ``basic_run.value.result`` contains the complete SimulationRun
"""

import logging
import random
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from compute_permit_sim.schemas import SimulationRun
from compute_permit_sim.services.config_manager import load_scenario
from compute_permit_sim.services.simulation_runner import run_single
from compute_permit_sim.vis.state.run_state import RunState, basic_run

if TYPE_CHECKING:
    from compute_permit_sim.vis.state.config import UIConfig
    from compute_permit_sim.vis.state.history import SessionHistory

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Headless simulation engine.

    Runs single-scenario simulations in a background daemon thread.
    State is communicated exclusively via the ``basic_run`` reactive:
    - ``phase="running"`` while the thread is active
    - ``phase="ready"`` with ``result`` populated when complete
    """

    def __init__(
        self,
        config: "UIConfig",
        history: "SessionHistory",
    ) -> None:
        self.config = config
        self.history = history

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_run(self) -> None:
        """Launch a headless run from the current UI config.

        Sets ``basic_run`` to ``running`` (one re-render → spinner),
        then starts a daemon thread.  On completion, ``basic_run`` is set
        to ``ready`` with the full result (one re-render → results).
        """
        if basic_run.value.is_running:
            logger.warning("start_run called while already running — ignoring")
            return

        ui_seed = self.config.seed.value
        run_seed = ui_seed if ui_seed is not None else random.randint(0, 2**31 - 1)
        scenario_config = self.config.to_scenario_config()
        scenario_config = scenario_config.model_copy(update={"seed": run_seed})

        logger.info(
            "Starting headless run: seed=%d (user-set=%s)",
            run_seed,
            ui_seed is not None,
        )

        # One update → spinner appears
        basic_run.set(RunState[SimulationRun](phase="running"))

        def _run() -> None:
            try:
                run: SimulationRun = run_single(scenario_config)
                logger.info(
                    "Headless run done: compliance=%.1f%%, steps=%d",
                    run.metrics.final_compliance * 100,
                    len(run.steps),
                )
                # Bookkeeping before result lands — panel sees complete state
                self.history.add_run(run)
                self.history.select_run(run)
                # One update → spinner clears into full results
                basic_run.set(RunState[SimulationRun](phase="ready", result=run))
            except Exception as e:
                logger.error("Error in headless run: %s", e, exc_info=True)
                basic_run.set(RunState[SimulationRun](phase="idle"))

        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------
    # Scenario / persistence helpers
    # ------------------------------------------------------------------

    def load_scenario(self, filename: str) -> None:
        """Load a scenario file into UI config."""
        logger.info("Loading scenario: %s", filename)
        try:
            config = load_scenario(filename)
            self.config.from_scenario_config(config)
            self.config.selected_scenario.value = config.name or filename
        except Exception as e:
            logger.error("Error loading scenario %s: %s", filename, e)

    def save_run(self, name_prefix: str = "run") -> str | None:
        """Persist the selected run to a JSON file."""
        run_to_save = self.history.selected_run.value
        if not run_to_save:
            logger.warning("save_run called with no selected run")
            return None

        run_dir = Path("runs") / run_to_save.id
        run_dir.mkdir(parents=True, exist_ok=True)
        filepath = run_dir / "full_run.json"
        with open(filepath, "w") as f:
            f.write(run_to_save.model_dump_json(indent=2))

        logger.info("Saved run to %s", filepath)
        return str(run_dir)
