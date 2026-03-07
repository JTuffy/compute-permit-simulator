import solara
import solara.lab

from compute_permit_sim.schemas import ScenarioConfig
from compute_permit_sim.vis.components import AutoConfigView
from compute_permit_sim.vis.components.dialogs import LoadScenarioDialog
from compute_permit_sim.vis.components.history import UnifiedHistoryList
from compute_permit_sim.vis.components.results import SidebarLabel
from compute_permit_sim.vis.state import engine
from compute_permit_sim.vis.state.config import ui_config
from compute_permit_sim.vis.state.history import session_history
from compute_permit_sim.vis.state.run_state import basic_run


@solara.component
def ParamView(config: ScenarioConfig):
    """Read-only configuration view."""
    AutoConfigView(schema=ScenarioConfig, model=config, readonly=True)


@solara.component
def ConfigPanel():
    with solara.Column(classes=["sidebar-compact"]):
        # Scenario Selection
        show_load, set_show_load = solara.use_state(False)

        def open_load_dialog():
            session_history.refresh_scenarios()
            set_show_load(True)

        LoadScenarioDialog(show_load, set_show_load)

        # Header: SCENARIO label + shortcut play icon + load button
        with solara.Row(
            style="align-items: center; margin-bottom: 8px;", justify="space-between"
        ):
            SidebarLabel("**SCENARIO**")
            with solara.Row(style="gap: 0;"):
                with solara.Tooltip("Run simulation"):
                    solara.Button(
                        icon_name="mdi-play",
                        on_click=engine.start_run,
                        icon=True,
                        small=True,
                        color="primary",
                        disabled=basic_run.value.is_running,
                    )
                solara.Button(
                    "Load",
                    on_click=open_load_dialog,
                    icon_name="mdi-folder-open",
                    small=True,
                    text=True,
                )

        AutoConfigView(
            schema=ScenarioConfig,
            model=ui_config,
            readonly=False,
            exclude=["name", "description"],
        )

        is_running = basic_run.value.is_running
        solara.Button(
            label="⏳ Running..." if is_running else "▶ Play",
            on_click=engine.start_run,
            color="primary",
            block=True,
            disabled=is_running,
        )

        # ── History — batch results + individual runs in one stream ────────
        solara.Markdown("---")
        with solara.Column(classes=["sidebar-history-section"]):
            SidebarLabel("**HISTORY**")
            UnifiedHistoryList()
