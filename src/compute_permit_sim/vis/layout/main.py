from pathlib import Path

import solara

from compute_permit_sim.vis.components.system import (
    SimulationController,
    UrlManager,
)
from compute_permit_sim.vis.panels.analysis import AnalysisPanel
from compute_permit_sim.vis.panels.config import ConfigPanel
from compute_permit_sim.vis.state.active import active_sim
from compute_permit_sim.vis.state.history import session_history


@solara.component
def EmptyState():
    with solara.Column(
        style="height: 60vh; justify-content: center; align-items: center; color: #888;"
    ):
        solara.Markdown("## Ready to Simulate")
        solara.Markdown("Configure parameters on the left and click **▶ Play**.")


@solara.component
def LoadingState():
    with solara.Column(
        style="height: 60vh; justify-content: center; align-items: center;"
    ):
        solara.v.ProgressCircular(indeterminate=True, color="primary", size=50)
        solara.Text("Simulating Scenario...", classes=["mt-4", "text-xl", "font-bold"])


@solara.component
def Page():
    # Inject CSS
    solara.Style(Path(__file__).parent.parent / "assets" / "style.css")

    # Sync URL State
    UrlManager()

    # Mount the controller (handles the play loop when is_playing becomes True)
    SimulationController()

    with solara.Sidebar():
        ConfigPanel()

    with solara.Column(style="height: 100vh; outline: none;"):
        solara.Title("Compute Permit Market Simulator")

        # --- Right Pane State Machine ---
        has_data = (active_sim.state.value.step_count > 0) or (
            session_history.selected_run.value is not None
        )
        is_playing = active_sim.state.value.is_playing

        if is_playing:
            LoadingState()
        elif not has_data:
            EmptyState()
        else:
            # Unified analysis view (no tabs)
            AnalysisPanel()
