"""Root page for the Solara application.

Right-pane state machine (centralized here):
    basic_run.phase == "running"          → RunSpinner (basic sim)
    mc_run.phase == "running"             → RunSpinner (Monte Carlo)
    sweep_run.phase == "running"          → RunSpinner (Sweep)
    grid_run.phase == "running"           → RunSpinner (Grid Sweep)
    mc_run.phase == "ready"               → BatchResultsPanel
    sweep_run.phase == "ready"            → BatchResultsPanel
    grid_run.phase == "ready"             → BatchResultsPanel
    basic_run.phase == "ready" OR history → AnalysisPanel
    else                                  → EmptyState
"""

import logging
from pathlib import Path

import solara
import solara.lab

from compute_permit_sim.vis.components.run_spinner import RunSpinner
from compute_permit_sim.vis.components.system import (
    SimulationController,
    UrlManager,
)
from compute_permit_sim.vis.logging_config import configure_logging
from compute_permit_sim.vis.panels.analysis import AnalysisPanel
from compute_permit_sim.vis.panels.batch import BatchPanel
from compute_permit_sim.vis.panels.batch_results import BatchResultsPanel
from compute_permit_sim.vis.panels.config import ConfigPanel
from compute_permit_sim.vis.state.history import session_history
from compute_permit_sim.vis.state.run_state import (
    basic_run,
    grid_run,
    mc_run,
    sweep_run,
)

configure_logging()
logger = logging.getLogger(__name__)

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
def Page():
    # Inject CSS
    solara.Style(Path(__file__).parent / "assets" / "style.css")

    # Sync URL State
    UrlManager()

    # No-op stub — headless runs don't need a controller loop
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
        with solara.lab.Tabs(background_color="transparent"):
            with solara.lab.Tab("Simulate", icon_name="mdi-play-circle-outline"):
                ConfigPanel()
            with solara.lab.Tab("Batch", icon_name="mdi-chart-bell-curve-cumulative"):
                BatchPanel()

    with solara.Column(style="height: 100vh; outline: none;"):
        solara.Title("Compute Permit Market Simulator")

        # --- Right Pane State Machine ---
        # All run types use the same RunState[T] pattern; this is the single
        # source of truth for what the right pane displays.
        basic = basic_run.value
        mc = mc_run.value
        sw = sweep_run.value
        gr = grid_run.value

        if basic.is_running:
            RunSpinner("Simulating\u2026")
        elif mc.is_running or sw.is_running or gr.is_running:
            RunSpinner("Running batch analysis\u2026")
        elif mc.is_ready or sw.is_ready or gr.is_ready:
            BatchResultsPanel()
        elif basic.is_ready or session_history.selected_run.value is not None:
            AnalysisPanel()
        else:
            EmptyState()
