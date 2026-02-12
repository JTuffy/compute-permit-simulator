import solara
import solara.lab

from compute_permit_sim.schemas import ScenarioConfig
from compute_permit_sim.services import engine
from compute_permit_sim.vis.components import RangeController, RangeView
from compute_permit_sim.vis.components.dialogs import LoadScenarioDialog
from compute_permit_sim.vis.components.history import RunHistoryList
from compute_permit_sim.vis.state.active import active_sim
from compute_permit_sim.vis.state.config import ui_config
from compute_permit_sim.vis.state.history import session_history


@solara.component
def ParamView(config: ScenarioConfig) -> solara.Element:
    """Read-only view of a ScenarioConfig."""
    with solara.lab.Tabs(vertical=True, align="left", dark=False):
        with solara.lab.Tab("General", style={"min-width": "auto"}):
            with solara.Column(style="opacity: 0.8; font-size: 0.9em;"):
                solara.InputInt(label="Steps", value=config.steps, disabled=True)
                solara.InputInt(label="N Agents", value=config.n_agents, disabled=True)
                solara.InputInt(
                    label="Token Cap (Q)",
                    value=int(config.market.token_cap),
                    disabled=True,
                )

        with solara.lab.Tab("Audit", style={"min-width": "auto"}):
            with solara.Column(style="opacity: 0.8; font-size: 0.9em;"):
                solara.InputFloat(
                    label="Penalty Amount",
                    value=config.audit.penalty_amount,
                    disabled=True,
                )
                solara.InputFloat(
                    label="Base Prob (pi_0)",
                    value=config.audit.base_prob,
                    disabled=True,
                )
                solara.InputFloat(
                    label="High Prob (pi_1)",
                    value=config.audit.high_prob,
                    disabled=True,
                )
                solara.InputFloat(
                    label="P(False Neg) 1-TPR",
                    value=config.audit.false_negative_rate,
                    disabled=True,
                )
                solara.InputFloat(
                    label="P(False Pos) FPR",
                    value=config.audit.false_positive_rate,
                    disabled=True,
                )
                solara.InputFloat(
                    label="Audit Cost",
                    value=config.audit.cost,
                    disabled=True,
                )

        with solara.lab.Tab("Lab", style={"min-width": "auto"}):
            with solara.Column(style="opacity: 0.8; font-size: 0.9em;"):
                RangeView(
                    "Gross Value Range",
                    config.lab.economic_value_min,
                    config.lab.economic_value_max,
                )
                RangeView(
                    "Risk Profile Range",
                    config.lab.risk_profile_min,
                    config.lab.risk_profile_max,
                )
                RangeView(
                    "Capacity Range",
                    config.lab.capacity_min,
                    config.lab.capacity_max,
                )
                solara.InputFloat(
                    label="Capability Value (V_b)",
                    value=config.lab.capability_value,
                    disabled=True,
                )
                solara.InputFloat(
                    label="Racing Factor (c_r)",
                    value=config.lab.racing_factor,
                    disabled=True,
                )


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

        # Load Dialog - using v.Card for proper sizing

        # General Parameters Card
        with solara.Card("General", style="margin-bottom: 6px;"):
            with solara.Column():
                solara.InputInt(label="Steps", value=ui_config.steps, dense=True)
                solara.InputInt(label="N Agents", value=ui_config.n_agents, dense=True)
                solara.InputFloat(
                    label="Token Cap Q", value=ui_config.token_cap, dense=True
                )

                # Seed Control
                def _update_seed(val):
                    try:
                        ui_config.seed.value = int(val) if val else None
                    except ValueError:
                        pass

                solara.InputText(
                    label="Seed (Optional)",
                    value=str(ui_config.seed.value)
                    if ui_config.seed.value is not None
                    else "",
                    on_value=_update_seed,
                )

        # Audit Policy Card
        with solara.Card("Audit Policy", style="margin-bottom: 6px;"):
            with solara.Column():
                solara.InputFloat(
                    label="Penalty (M$)", value=ui_config.penalty, dense=True
                )
                solara.InputFloat(
                    label="Base π₀", value=ui_config.base_prob, dense=True
                )
                solara.InputFloat(
                    label="High π₁", value=ui_config.high_prob, dense=True
                )
                solara.InputFloat(
                    label="Signal TPR", value=ui_config.signal_tpr, dense=True
                )
                solara.InputFloat(
                    label="Signal FPR", value=ui_config.signal_fpr, dense=True
                )

        # Lab Generation Card
        with solara.Card("Lab Generation", style="margin-bottom: 6px;"):
            with solara.Column():
                RangeController(
                    "Economic Value",
                    ui_config.economic_value_min,
                    ui_config.economic_value_max,
                )
                RangeController(
                    "Risk Profile",
                    ui_config.risk_profile_min,
                    ui_config.risk_profile_max,
                )
                RangeController(
                    "Capacity", ui_config.capacity_min, ui_config.capacity_max
                )

                # Missing Lab Parameters
                solara.Markdown("---", style="margin: 8px 0;")
                solara.InputFloat(
                    label="Capability Vb", value=ui_config.capability_value, dense=True
                )
                solara.InputFloat(
                    label="Racing Factor cr", value=ui_config.racing_factor, dense=True
                )
                solara.InputFloat(
                    label="Reputation Sen. R",
                    value=ui_config.reputation_sensitivity,
                    dense=True,
                )
                solara.InputFloat(
                    label="Audit Coeff c(i)",
                    value=ui_config.audit_coefficient,
                    dense=True,
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
