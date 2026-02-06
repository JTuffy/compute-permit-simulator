import solara

from compute_permit_sim.services import engine
from compute_permit_sim.vis.state.history import session_history


@solara.component
def LoadScenarioDialog(show: bool, set_show: callable):
    """Dialog for selecting and loading a scenario file."""
    selected_file, set_selected_file = solara.use_state(None)

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
