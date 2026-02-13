import solara
import solara.lab

from compute_permit_sim.schemas import ScenarioConfig
from compute_permit_sim.vis.components import AutoConfigView
from compute_permit_sim.vis.components.dialogs import LoadScenarioDialog
from compute_permit_sim.vis.components.history import RunHistoryList
from compute_permit_sim.vis.state import engine
from compute_permit_sim.vis.state.active import active_sim
from compute_permit_sim.vis.state.config import ui_config
from compute_permit_sim.vis.state.history import session_history


@solara.component
def ParamView(config: ScenarioConfig) -> solara.Element:
    """Read-only view of a ScenarioConfig."""
    return AutoConfigView(schema=ScenarioConfig, model=config, readonly=True)


@solara.component
def ConfigPanel():
    # Wrap entire panel in compact styling
    with solara.Column(classes=["sidebar-compact"]):
        # Scenario Selection (New File-based)
        show_load, set_show_load = solara.use_state(False)

        def open_load_dialog():
            session_history.refresh_scenarios()
            set_show_load(True)

        LoadScenarioDialog(show_load, set_show_load)

        # Header with Load and Play buttons
        with solara.Row(
            style="align-items: center; margin-bottom: 8px;", justify="space-between"
        ):
            solara.Markdown("**SCENARIO**", style="font-size: 0.9rem; opacity: 0.7;")
            with solara.Row():
                solara.Button(
                    icon_name="mdi-play",
                    on_click=engine.start_run,
                    icon=True,
                    small=True,
                    color="primary",
                    disabled=active_sim.state.value.is_playing,
                )
                solara.Button(
                    "Load",
                    on_click=open_load_dialog,
                    icon_name="mdi-folder-open",
                    small=True,
                    text=True,
                )

        # Run Settings (Seed)
        def _update_seed(val):
            try:
                ui_config.seed.value = int(val) if val else None
            except ValueError:
                pass

        with solara.Card("Run Settings", style="margin-bottom: 6px;"):
            solara.InputText(
                label="Seed (Optional)",
                value=str(ui_config.seed.value)
                if ui_config.seed.value is not None
                else "",
                on_value=_update_seed,
            )

        # Auto-Generated Config
        # Exclude seed.
        AutoConfigView(
            schema=ScenarioConfig,
            model=ui_config,
            readonly=False,
            exclude=["seed", "name", "description"],
        )

        is_running = active_sim.state.value.is_playing
        solara.Button(
            label="⏳ Running..." if is_running else "▶ Play",
            on_click=engine.start_run,
            color="primary",
            block=True,
            disabled=is_running,
            style="font-weight: 600;",
        )

        # Run History Section (Compact)
        solara.Markdown("---")
        solara.Markdown(
            "**RUN HISTORY**",
            style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 4px;",
        )
        with solara.Column(classes=["run-history-compact"]):
            RunHistoryList()
