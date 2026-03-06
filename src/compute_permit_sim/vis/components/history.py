import solara
import solara.lab

from compute_permit_sim.schemas import SimulationRun
from compute_permit_sim.services.config_manager import save_scenario
from compute_permit_sim.vis.components.dialogs import RunConfigDialog
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

    # Theme-aware selection highlight — teal/primary tint via CSS class
    selected_style = (
        "background: rgba(var(--v-primary-base), 0.12); border-radius: 4px;"
        if is_selected
        else ""
    )

    with solara.Row(
        style=(f"{selected_style} padding: 2px; align-items: center;"),
        classes=["hover-bg"],
    ):
        # Shared config dialog — same component as AnalysisSummary
        RunConfigDialog(
            config=run.config,
            title=f"Run: {display_id}",
            subtitle=f"Created: {ts_str}",
            metrics=run.metrics,
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

        # Export Actions — use sim_id for readable filenames
        from compute_permit_sim.vis.export import export_run_to_csv, export_run_to_excel

        fname_base = run.sim_id or run.id
        excel_fname = f"{fname_base}.xlsx"
        csv_fname = f"{fname_base}.csv"

        with solara.Tooltip("Export to Excel"):
            with solara.FileDownload(
                filename=excel_fname,
                data=lambda: export_run_to_excel(run, output_path=""),
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ):
                solara.Button(icon_name="mdi-file-excel", icon=True, small=True)

        with solara.Tooltip("Export to CSV (Step Data)"):
            with solara.FileDownload(
                filename=csv_fname,
                data=lambda: export_run_to_csv(run, output_path=""),
                mime_type="text/csv",
            ):
                solara.Button(icon_name="mdi-file-delimited", icon=True, small=True)

            # Pure HTML/JS Button: copy shareable link
            url = f"?id={run.url_id}"
            btn_html = (
                f"""<button onclick="navigator.clipboard.writeText(window.location.origin + window.location.pathname + '{url}'); alert('Link copied!');" """
                f"""style="background:none; border:none; cursor:pointer; padding:6px; color:var(--v-primary-base,#1565C0); border-radius:50%; transition: background 0.2s;" """
                f"""onmouseover="this.style.background='rgba(33,150,243,0.1)'" """
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
