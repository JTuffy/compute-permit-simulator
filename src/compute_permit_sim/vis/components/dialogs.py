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
    """Dialog for selecting and loading a scenario by display name.

    Uses ``session_history.scenario_name_map`` so the dropdown shows
    human-readable names (e.g. "High Enforcement") rather than filenames.
    Shows the scenario's ``notes`` field as a preview when available.
    """
    from compute_permit_sim.services.config_manager import load_scenario

    name_map = session_history.scenario_name_map.value  # {display_name -> filename}
    display_names = sorted(name_map.keys())
    selected_name, set_selected_name = solara.use_state(cast(str | None, None))

    # Load notes for the selected scenario (lightweight — just metadata fields)
    notes_preview: str = ""
    if selected_name:
        filename = name_map.get(selected_name)
        if filename:
            try:
                cfg = load_scenario(filename)
                notes_preview = cfg.notes
            except Exception:  # noqa: BLE001
                pass

    def do_load() -> None:
        if selected_name:
            filename = name_map.get(selected_name, selected_name)
            engine.load_scenario(filename)
            set_show(False)

    with solara.v.Dialog(
        v_model=show,
        on_v_model=set_show,
        max_width=440,
        persistent=False,
    ):
        with solara.v.Card(style="overflow: visible;"):
            with solara.v.CardTitle():
                solara.Text("Load Scenario")
            with solara.v.CardText(style="padding: 16px;"):
                if display_names:
                    solara.Select(
                        label="Scenario",
                        values=display_names,
                        value=selected_name,
                        on_value=set_selected_name,
                    )
                    if notes_preview:
                        solara.Text(
                            notes_preview,
                            style=(
                                "font-size: 0.78rem; opacity: 0.65; margin-top: 6px; "
                                "white-space: pre-wrap; font-style: italic;"
                            ),
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
                    disabled=(not selected_name),
                )
