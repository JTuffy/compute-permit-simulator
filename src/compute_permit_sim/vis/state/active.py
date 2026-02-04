"""Active simulation state - the currently running model and its live data."""

import pandas as pd
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
        self.agents_df.value = None
        self.current_run_steps = []

    def update_from_model(self, model) -> None:
        """Update derived state from model after a step."""
        if not model:
            return

        # Update agents DataFrame
        agents = model.get_all_agent_data()
        self.agents_df.value = pd.DataFrame(agents)

        # Update time series
        compliance = (
            sum(a.get("Compliant", False) for a in agents) / len(agents)
            if agents
            else 0
        )
        self.compliance_history.value = self.compliance_history.value + [compliance]
        self.price_history.value = self.price_history.value + [
            model.market.current_price
        ]


# Singleton instance
active_sim = ActiveSimulation()
