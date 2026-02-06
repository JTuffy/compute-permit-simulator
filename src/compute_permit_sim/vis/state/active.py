"""Active simulation state - the currently running model and its live data."""

import solara

from compute_permit_sim.schemas import StepResult


class ActiveSimulation:
    """State of the currently running simulation.

    This class holds reactive state for the live model, step count,
    and derived data like compliance/price histories.
    """

    def __init__(self):
        # --- Model Reference ---
        self.model = solara.reactive(None)  # ComputePermitModel | None

        # --- Step Tracking ---
        self.step_count = solara.reactive(0)
        self.is_playing = solara.reactive(False)
        self.actual_seed = solara.reactive(None)

        # --- Time Series (for live charting) ---
        self.compliance_history = solara.reactive([])  # List[float]
        self.price_history = solara.reactive([])  # List[float]
        self.wealth_history_compliant = solara.reactive([])  # List[float]
        self.wealth_history_non_compliant = solara.reactive([])  # List[float]

        # --- Current Step Snapshot ---
        self.agents_df = solara.reactive(None)  # pd.DataFrame | None

        # --- Step Results (for eventual packing) ---
        self.current_run_steps: list[StepResult] = []

    def reset(self) -> None:
        """Reset all active simulation state."""
        self.model.value = None
        self.step_count.value = 0
        self.is_playing.value = False
        self.compliance_history.value = []
        self.price_history.value = []
        self.wealth_history_compliant.value = []
        self.wealth_history_non_compliant.value = []
        self.agents_df.value = None
        self.current_run_steps = []


# Singleton instance
active_sim = ActiveSimulation()
