from typing import Callable, cast

import solara

from compute_permit_sim.schemas import RunMetrics, ScenarioConfig
from compute_permit_sim.vis.components.auto_config import AutoConfigView
from compute_permit_sim.vis.state import engine
from compute_permit_sim.vis.state.history import session_history


@solara.component
def RunConfigDialog(
    config: ScenarioConfig,
    title: str,
    metrics: RunMetrics | None = None,
    subtitle: str | None = None,
):
    """Reusable ⓘ icon button → dialog showing config params + optional metrics.

    Used by both RunHistoryItem (sidebar) and AnalysisSummary (results pane)
    so there is exactly one copy of this UI.
    """
    show, set_show = solara.use_state(False)

    with solara.Tooltip("View configuration"):
        solara.Button(
            icon_name="mdi-information-outline",
            icon=True,
            small=True,
            on_click=lambda: set_show(True),
        )

    with solara.v.Dialog(v_model=show, on_v_model=set_show, max_width=520):
        with solara.v.Card():
            with solara.v.CardTitle(
                class_="primary white--text",
                style="padding: 12px 16px;",
            ):
                solara.Text(title)

            with solara.v.CardText(style="padding: 12px 16px;"):
                if subtitle:
                    solara.Text(
                        subtitle,
                        style="opacity: 0.65; font-size: 0.82rem; margin-bottom: 8px;",
                    )

                # Config view — uses config-view CSS class for consistent styling
                AutoConfigView(
                    schema=ScenarioConfig,
                    model=config,
                    readonly=True,
                    render_mode="tabs",
                )

                if metrics:
                    solara.Markdown("---")
                    with solara.Columns([1, 1]):
                        solara.Markdown(
                            f"**Final Compliance:** {metrics.final_compliance:.1%}"
                        )
                        solara.Markdown(f"**Final Price:** ${metrics.final_price:.2f}")

            with solara.v.CardActions():
                solara.v.Spacer()
                solara.Button(
                    "Close",
                    on_click=lambda: set_show(False),
                    text=True,
                    color="primary",
                )


@solara.component
def LoadScenarioDialog(show: bool, set_show: Callable[[bool], None]):
    """Dialog for selecting and loading a scenario file."""
    selected_file, set_selected_file = solara.use_state(cast(str | None, None))

    def do_load():
        if selected_file:
            engine.load_scenario(selected_file)
            set_show(False)

    with solara.v.Dialog(
        v_model=show,
        on_v_model=set_show,
        max_width=400,
        persistent=False,
    ):
        with solara.v.Card(style="overflow: visible;"):
            with solara.v.CardTitle():
                solara.Text("Load Scenario Template")
            with solara.v.CardText(style="padding: 16px;"):
                if session_history.available_scenarios.value:
                    solara.Select(
                        label="Choose File",
                        values=session_history.available_scenarios.value,
                        value=selected_file,
                        on_value=set_selected_file,
                    )
                else:
                    solara.Markdown("_No scenarios found in scenarios/_")
            with solara.v.CardActions():
                solara.v.Spacer()
                solara.Button("Cancel", on_click=lambda: set_show(False), text=True)
                solara.Button(
                    "Load",
                    on_click=do_load,
                    color="primary",
                    disabled=(not selected_file),
                )
