import solara
import solara.lab

from compute_permit_sim.schemas import ScenarioConfig, SimulationRun
from compute_permit_sim.services.config_manager import save_scenario
from compute_permit_sim.vis.components import AutoConfigView
from compute_permit_sim.vis.state.history import session_history


@solara.component
def RunHistoryItem(run: SimulationRun, is_selected: bool) -> None:
    """Individual item in the history list."""

    # Label generation
    if run.sim_id:
        display_id = run.sim_id
    else:
        # Fallback to timestamp parts
        display_id = run.id
        try:
            display_id = run.id.split("_")[1]
        except IndexError:
            pass

    # Request: Just the ID
    label = display_id

    # Actions

    def view_run():
        session_history.selected_run.value = run

    show_menu, set_show_menu = solara.use_state(False)

    # Rich Tooltip Construction
    try:
        parts = run.id.split("_")
        ts_str = f"{parts[0]}-{parts[1]}"
    except IndexError:
        ts_str = "Unknown"

    c = run.config

    bg_color = "#e0f2f1" if is_selected else "transparent"

    with solara.Row(
        style=(f"background-color: {bg_color}; padding: 2px; align-items: center;"),
        classes=["hover-bg"],
    ):
        # Info Button Area - Using robust Click-to-Open Dialog
        with solara.v.Dialog(
            v_model=show_menu, on_v_model=set_show_menu, max_width=500
        ):
            with solara.v.Card():
                # Header
                with solara.v.CardTitle(
                    style="background: #2196F3; color: white; padding: 12px 16px;"
                ):
                    solara.Text(f"Run: {display_id}")

                with solara.v.CardText(style="padding: 16px;"):
                    # Timestamp
                    solara.Text(
                        f"Created: {ts_str}", style="opacity: 0.7; font-size: 0.85rem;"
                    )

                    solara.Markdown("---", style="margin: 12px 0;")
                    AutoConfigView(
                        schema=ScenarioConfig,
                        model=c,
                        readonly=True,
                        collapsible=True,
                    )
                    solara.Markdown("---", style="margin: 12px 0;")

                    # Metrics (always available via Typed Object)
                    solara.HTML(
                        tag="h4",
                        unsafe_innerHTML="Results",
                        style="margin: 16px 0 8px 0; border-bottom: 1px solid #eee; padding-bottom: 4px;",
                    )
                    with solara.Columns([1, 1]):
                        solara.Markdown(
                            f"**Final Compliance:** {run.metrics.final_compliance:.1%}"
                        )
                        solara.Markdown(
                            f"**Final Price:** ${run.metrics.final_price:.2f}"
                        )

                with solara.v.CardActions():
                    solara.v.Spacer()
                    solara.Button(
                        "Close",
                        on_click=lambda: set_show_menu(False),
                        text=True,
                        color="primary",
                    )

        # The Activator Button - Using solara.Button for proper event handling
        def open_info_dialog():
            set_show_menu(True)

        solara.Button(
            icon_name="mdi-information-outline",
            on_click=open_info_dialog,
            icon=True,
            small=True,
        )

        # View Button
        solara.Button(
            label,
            on_click=view_run,
            text=True,
            style="text-transform: none; text-align: left; flex-grow: 1;",
            color="primary" if is_selected else None,
        )

        # Save Scenario
        show_save, set_show_save = solara.use_state(False)
        save_name, set_save_name = solara.use_state(f"scenario_{run.id}")

        def perform_save():
            fname = save_name if save_name.endswith(".json") else f"{save_name}.json"
            save_scenario(run.config, fname)
            set_show_save(False)

        with solara.Tooltip("Save as Scenario Template"):
            solara.Button(
                icon_name="mdi-content-save",
                on_click=lambda: set_show_save(True),
                icon=True,
                small=True,
            )

        # Save Dialog - placed after button, using v.Card for proper sizing
        with solara.v.Dialog(
            v_model=show_save,
            on_v_model=set_show_save,
            max_width=400,
            persistent=False,
        ):
            with solara.v.Card(style="overflow: visible;"):
                with solara.v.CardTitle():
                    solara.Text("Save Scenario")
                with solara.v.CardText(style="padding: 16px;"):
                    solara.InputText(
                        label="Filename", value=save_name, on_value=set_save_name
                    )
                with solara.v.CardActions():
                    solara.v.Spacer()
                    solara.Button(
                        "Cancel", on_click=lambda: set_show_save(False), text=True
                    )
                    solara.Button("Save", on_click=perform_save, color="primary")

        # Excel Export
        def export_excel():
            from compute_permit_sim.vis.export import export_run_to_excel

            try:
                result = export_run_to_excel(run)
                print(
                    f"Exported to: {result.decode() if isinstance(result, bytes) else result}"
                )
            except Exception as e:
                print(f"Export failed: {e}")
                import traceback

                traceback.print_exc()

        with solara.Tooltip("Export to Excel"):
            solara.Button(
                icon_name="mdi-file-excel",
                on_click=export_excel,
                icon=True,
                small=True,
            )

            # Pure HTML/JS Button: "Just copy the ID"
            # This bypasses Solara's event loop and works directly in the browser.
            url = f"?id={run.url_id}"

            # Using a simplified HTML button that looks like a Solara button (MDI icon)
            # relying on default button styling or inline styles.
            btn_html = (
                f"""<button onclick="navigator.clipboard.writeText(window.location.origin + window.location.pathname + '{url}'); alert('Link copied!');" """
                f"""style="background:none; border:none; cursor:pointer; padding:6px; color:#2196F3; border-radius:50%; transition: background 0.2s;" """
                f"""onmouseover="this.style.background='rgba(33, 150, 243, 0.1)'" """
                f"""onmouseout="this.style.background='none'" """
                f"""title="Copy shareable link">"""
                f"""<i class="mdi mdi-link-variant" style="font-size:20px;"></i>"""
                f"""</button>"""
            )
            solara.HTML(tag="div", unsafe_innerHTML=btn_html)


@solara.component
def RunHistoryList():
    if not session_history.run_history.value:
        solara.Markdown("_No runs yet._")
        return

    # Compact list with custom items
    with solara.Column():
        for run in session_history.run_history.value:
            is_selected = (session_history.selected_run.value is not None) and (
                session_history.selected_run.value.id == run.id
            )
            RunHistoryItem(run, is_selected)
