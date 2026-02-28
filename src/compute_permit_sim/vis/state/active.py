"""Active simulation state - the currently running model and its live data."""

import pandas as pd
import solara
from pydantic import BaseModel, ConfigDict, Field

from compute_permit_sim.schemas import StepResult
from compute_permit_sim.services.mesa_model import ComputePermitModel


class SimulationState(BaseModel):
    """Unified state object for the active simulation.

    This replaces multiple individual reactive variables to prevent
    cascading re-renders during updates.
    """

    model: ComputePermitModel | None = Field(
        default=None, description="The active Mesa model"
    )
    step_count: int = 0
    is_playing: bool = False
    actual_seed: int | None = None
    compliance_history: list[float] = Field(default_factory=list)
    price_history: list[float] = Field(default_factory=list)
    wealth_history_compliant: list[float] = Field(default_factory=list)
    wealth_history_non_compliant: list[float] = Field(default_factory=list)
    agents_df: pd.DataFrame | None = Field(default=None, description="Pandas DataFrame")
    current_run_steps: list[StepResult] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ActiveSimulation:
    """State of the currently running simulation.

    This class holds a SINGLE reactive state object for the live model.
    """

    def __init__(self):
        # Unified State
        self.state = solara.reactive(SimulationState())

    def reset(self) -> None:
        """Reset all active simulation state."""
        self.state.value = SimulationState()

    def update(self, **kwargs) -> None:
        """Update specific fields of the state efficiently.

        Creates a shallow copy with updated fields to trigger ONE re-render.
        """
        current = self.state.value
        # Use model_copy(update=...) for Pydantic v2
        self.state.value = current.model_copy(update=kwargs)


# Singleton instance
active_sim = ActiveSimulation()
