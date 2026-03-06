"""Root page for the Solara application.

Logic is distributed across `vis/panels`, `vis/components`, and `vis/state`.
"""

import logging
from pathlib import Path

import solara
import solara.lab

from compute_permit_sim.vis.components.system import (
    SimulationController,
    UrlManager,
)
from compute_permit_sim.vis.panels.analysis import AnalysisPanel
from compute_permit_sim.vis.panels.config import ConfigPanel
from compute_permit_sim.vis.state.active import active_sim
from compute_permit_sim.vis.state.history import session_history

# --- Logging Configuration ---
logger = logging.getLogger("compute_permit_sim")
logger.setLevel(logging.INFO)
if logger.handlers:
    logger.handlers.clear()

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
logger.addHandler(stream_handler)

# ---------------------------------------------------------------------------
# Vuetify theme — applied once at module load, cascades to all components
# ---------------------------------------------------------------------------
# Light palette
solara.lab.theme.themes.light.primary = "#1565C0"  # deep blue
solara.lab.theme.themes.light.secondary = "#546E7A"  # blue-grey
solara.lab.theme.themes.light.accent = "#00ACC1"  # teal
solara.lab.theme.themes.light.success = "#2E7D32"  # forest green
solara.lab.theme.themes.light.warning = "#E65100"  # deep orange
solara.lab.theme.themes.light.info = "#0277BD"  # ocean blue
solara.lab.theme.themes.light.error = "#B71C1C"  # dark red

# Dark palette (same hues, lightened for dark backgrounds)
solara.lab.theme.themes.dark.primary = "#42A5F5"  # sky blue
solara.lab.theme.themes.dark.secondary = "#78909C"  # blue-grey 400
solara.lab.theme.themes.dark.accent = "#26C6DA"  # teal 300
solara.lab.theme.themes.dark.success = "#66BB6A"  # green 400
solara.lab.theme.themes.dark.warning = "#FFA726"  # orange 400
solara.lab.theme.themes.dark.info = "#29B6F6"  # light-blue 400
solara.lab.theme.themes.dark.error = "#EF5350"  # red 400

# Start in dark mode — significantly more polished for a simulator tool
solara.lab.theme.dark = True


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
    solara.Style(Path(__file__).parent / "assets" / "style.css")

    # Sync URL State
    UrlManager()

    # Mount the controller (handles the play loop when is_playing becomes True)
    SimulationController()

    # --- Top App Bar: dark/light toggle in top-right ---
    with solara.AppBar():
        solara.v.Spacer()
        is_dark = solara.lab.theme.dark

        def toggle_theme():
            solara.lab.theme.dark = not solara.lab.theme.dark

        solara.Button(
            label="",
            icon_name="mdi-weather-night" if is_dark else "mdi-weather-sunny",
            icon=True,
            on_click=toggle_theme,
            style="color: rgba(255,255,255,0.85);",
        )

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
