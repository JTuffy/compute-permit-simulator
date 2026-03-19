"""Session history state — past runs and scenario management."""

from __future__ import annotations

import solara

from compute_permit_sim.schemas import SimulationRun
from compute_permit_sim.schemas.batch import (
    GridSweepResult,
    MonteCarloResult,
    SweepResult,
)

# Union type for batch results — MC aggregate, 1D sweep, or 2D grid sweep.
BatchResult = MonteCarloResult | SweepResult | GridSweepResult


class SessionHistory:
    """State for run history, batch result history, and scenario selection.

    Basic runs go into ``run_history`` (browsable via ``RunHistoryList``).
    Batch results (MC + sweep) go into ``batch_results`` (browsable via
    ``BatchHistoryList`` in the batch sidebar tab).
    """

    def __init__(self) -> None:
        # --- Basic run history ---
        self.run_history: solara.Reactive[list[SimulationRun]] = solara.reactive([])
        self.selected_run: solara.Reactive[SimulationRun | None] = solara.reactive(None)

        # --- Batch result history (MonteCarloResult | SweepResult) ---
        self.batch_results: solara.Reactive[list[BatchResult]] = solara.reactive([])

        # --- Available Scenarios ---
        # scenario_name_map: {display_name -> relative_filename}
        from compute_permit_sim.services.config_manager import (
            list_scenario_names,
            list_scenarios,
        )

        self.available_scenarios = solara.reactive(list_scenarios())
        pairs = list_scenario_names()
        self.scenario_name_map: solara.Reactive[dict[str, str]] = solara.reactive(
            {name: filename for name, filename in pairs}
        )

    def add_run(self, run: SimulationRun) -> None:
        """Add a completed basic run to history."""
        self.run_history.value = [run] + self.run_history.value

    def select_run(self, run: SimulationRun | None) -> None:
        """Select a basic run for detailed viewing."""
        self.selected_run.value = run

    def clear_selection(self) -> None:
        """Clear the selected basic run (return to live view)."""
        self.selected_run.value = None

    def add_batch_result(self, result: BatchResult) -> None:
        """Add a completed batch result (MonteCarloResult or SweepResult) to history."""
        self.batch_results.value = [result] + self.batch_results.value

    def refresh_scenarios(self) -> None:
        """Refresh the list of available scenario files and name map."""
        from compute_permit_sim.services.config_manager import (
            list_scenario_names,
            list_scenarios,
        )

        self.available_scenarios.value = list_scenarios()
        pairs = list_scenario_names()
        self.scenario_name_map.value = {name: filename for name, filename in pairs}


# Singleton instance
session_history = SessionHistory()
