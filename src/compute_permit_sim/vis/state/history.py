"""Session history state - past runs and scenario management."""

import solara

from compute_permit_sim.schemas import SimulationRun


class SessionHistory:
    """State for run history and scenario selection.

    This class manages the collection of past simulation runs
    and the list of available scenario files.
    """

    def __init__(self):
        # --- Run History ---
        self.run_history: solara.Reactive[list[SimulationRun]] = solara.reactive([])
        self.selected_run: solara.Reactive[SimulationRun | None] = solara.reactive(None)

        # --- Available Scenarios ---
        # --- Available Scenarios ---
        from compute_permit_sim.services.config_manager import list_scenarios

        self.available_scenarios = solara.reactive(list_scenarios())

    def add_run(self, run: SimulationRun) -> None:
        """Add a completed run to history."""
        self.run_history.value = [run] + self.run_history.value

    def select_run(self, run: SimulationRun | None) -> None:
        """Select a run for detailed viewing."""
        self.selected_run.value = run

    def clear_selection(self) -> None:
        """Clear the selected run (return to live view)."""
        self.selected_run.value = None

    def refresh_scenarios(self) -> None:
        """Refresh the list of available scenario files."""
        """Refresh the list of available scenario files."""
        from compute_permit_sim.services.config_manager import list_scenarios

        self.available_scenarios.value = list_scenarios()


# Singleton instance
session_history = SessionHistory()
