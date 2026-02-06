import solara
import solara.lab

from compute_permit_sim.schemas import SimulationRun
from compute_permit_sim.services.config_manager import save_scenario
from compute_permit_sim.services.simulation import engine
from compute_permit_sim.vis.state.history import session_history


@solara.component
def RunHistoryItem(run: SimulationRun, is_selected: bool) -> solara.Element:
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
    def load_config():
        engine.restore_config(run)

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

                    # General Config
                    solara.HTML(
                        tag="h4",
                        unsafe_innerHTML="General",
                        style="margin: 16px 0 8px 0; border-bottom: 1px solid #eee; padding-bottom: 4px;",
                    )
                    with solara.Columns([1, 1, 1]):
                        solara.Markdown(f"**Steps:** {c.steps}")
                        solara.Markdown(f"**Agents:** {c.n_agents}")
                        solara.Markdown(f"**Token Cap:** {int(c.market.token_cap)}")

                    # Audit Config
                    solara.HTML(
                        tag="h4",
                        unsafe_innerHTML="Audit Policy",
                        style="margin: 16px 0 8px 0; border-bottom: 1px solid #eee; padding-bottom: 4px;",
                    )
                    with solara.Columns([1, 1]):
                        with solara.Column():
                            solara.Markdown(
                                f"**Base Prob (π₀):** {c.audit.base_prob:.2%}"
                            )
                            solara.Markdown(
                                f"**High Prob (π₁):** {c.audit.high_prob:.2%}"
                            )
                            solara.Markdown(
                                f"**Backcheck:** {c.audit.backcheck_prob:.2%}"
                            )
                        with solara.Column():
                            solara.Markdown(
                                f"**Penalty:** ${c.audit.penalty_amount:.0f}"
                            )
                            solara.Markdown(
                                f"**TPR:** {1 - c.audit.false_negative_rate:.2%}"
                            )
                            solara.Markdown(
                                f"**FPR:** {c.audit.false_positive_rate:.2%}"
                            )
                            solara.Markdown(f"**Cost:** ${c.audit.cost:.2f}")

                    # Lab Config
                    solara.HTML(
                        tag="h4",
                        unsafe_innerHTML="Lab Parameters",
                        style="margin: 16px 0 8px 0; border-bottom: 1px solid #eee; padding-bottom: 4px;",
                    )
                    with solara.Columns([1, 1]):
                        with solara.Column():
                            solara.Markdown(
                                f"**Economic Value:** {c.lab.economic_value_min:.2f} - {c.lab.economic_value_max:.2f}"
                            )
                            solara.Markdown(
                                f"**Risk Profile:** {c.lab.risk_profile_min:.2f} - {c.lab.risk_profile_max:.2f}"
                            )
                            solara.Markdown(
                                f"**Capacity:** {c.lab.capacity_min:.2f} - {c.lab.capacity_max:.2f}"
                            )
                        with solara.Column():
                            solara.Markdown(
                                f"**Capability Vb:** {c.lab.capability_value:.2f}"
                            )
                            solara.Markdown(
                                f"**Racing Factor cr:** {c.lab.racing_factor:.2f}"
                            )
                            solara.Markdown(
                                f"**Reputation β:** {c.lab.reputation_sensitivity:.2f}"
                            )
                            solara.Markdown(
                                f"**Audit Coeff:** {c.lab.audit_coefficient:.2f}"
                            )

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

        # Load Config
        with solara.Tooltip("Load these parameters to Config Panel"):
            solara.Button(
                icon_name="mdi-upload",
                on_click=load_config,
                icon=True,
                small=True,
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
                output_path = export_run_to_excel(run)
                print(f"Exported to: {output_path}")
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
