import pandas as pd
import solara
import solara.lab

from compute_permit_sim.infrastructure.config_manager import save_scenario
from compute_permit_sim.vis.components import (
    QuantitativeScatterPlot,
    RangeController,
    RangeView,
)
from compute_permit_sim.vis.state import manager

# Custom CSS for compactness and hiding Solara watermark
DENSITY_CSS = """
.v-application .v-card__text { padding: 8px !important; }
.v-application .v-card__title { padding: 8px 12px !important; font-size: 1rem !important; }
.solara-markdown p { margin-bottom: 4px !important; }
footer { display: none !important; } 
"""

# --- Components ---


@solara.component
def SimulationController():
    """Invisible component to handle the play loop."""
    solara.lab.use_task(manager.play_loop, dependencies=[manager.is_playing.value])
    return solara.Div(style="display: none;")


@solara.component
def ParamView(config):
    """Read-only view of a ScenarioConfig."""
    with solara.lab.Tabs(vertical=True, align="left", dark=False):
        with solara.lab.Tab("General", style={"min-width": "auto"}):
            with solara.Column(gap="0px", style="opacity: 0.8; font-size: 0.9em;"):
                solara.InputInt(label="Steps", value=config.steps, disabled=True)
                solara.InputInt(label="N Agents", value=config.n_agents, disabled=True)
                solara.InputInt(
                    label="Token Cap (Q)",
                    value=int(config.market.token_cap),
                    disabled=True,
                )

        with solara.lab.Tab("Audit", style={"min-width": "auto"}):
            with solara.Column(gap="0px", style="opacity: 0.8; font-size: 0.9em;"):
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

        with solara.lab.Tab("Lab", style={"min-width": "auto"}):
            with solara.Column(gap="0px", style="opacity: 0.8; font-size: 0.9em;"):
                RangeView(
                    "Gross Value Range",
                    config.lab.gross_value_min,
                    config.lab.gross_value_max,
                )
                RangeView(
                    "Risk Profile Range",
                    config.lab.risk_profile_min,
                    config.lab.risk_profile_max,
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
def RunHistoryItem(run, is_selected):
    """Individual item in the history list."""

    # Label generation
    if run.metrics:
        comp = run.metrics.get("final_compliance", 0)
        price = run.metrics.get("final_price", 0)
        try:
            display_id = run.id.split("_")[1]
        except IndexError:
            display_id = run.id
        label = f"{display_id} (C:{comp:.0%} ${price:.0f})"
    else:
        label = f"{run.id} ({len(run.steps)})"

    # Actions
    def load_config():
        manager.restore_config(run)

    def view_run():
        manager.selected_run.value = run

    # Rich Tooltip Construction
    try:
        parts = run.id.split("_")
        ts_str = f"{parts[0]}-{parts[1]}"
    except IndexError:
        ts_str = "Unknown"

    c = run.config
    tooltip_text = (
        f"Run: {run.id}\n"
        f"Time: {ts_str}\n"
        f"cfg: {c.n_agents} agents, {c.steps} steps\n"
        f"Token Cap: {c.market.token_cap}"
    )

    if run.metrics and "fraud_detected" in run.metrics:
        tooltip_text += f"\nFraud Caught: {run.metrics['fraud_detected']}"

    bg_color = "#e0f2f1" if is_selected else "transparent"

    with solara.Row(
        style=(f"background-color: {bg_color}; padding: 2px; align-items: center;"),
        classes=["hover-bg"],
    ):
        # View Button (Main interaction)
        with solara.Tooltip(tooltip_text):
            solara.Button(
                label,
                on_click=view_run,
                text=True,
                style="text-transform: none; text-align: left; flex-grow: 1;",
                color="primary" if is_selected else None,
            )

        # Load Config Button
        with solara.Tooltip("Load these parameters to Config Panel"):
            solara.Button(
                icon_name="mdi-upload",
                on_click=load_config,
                icon=True,
                small=True,
            )

        # Save Scenario Button
        show_save, set_show_save = solara.use_state(False)
        save_name, set_save_name = solara.use_state(f"scenario_{run.id}")

        def perform_save():
            # Add .json if missing
            fname = save_name if save_name.endswith(".json") else f"{save_name}.json"
            save_scenario(run.config, fname)
            set_show_save(False)
            # Maybe notify user?

        with solara.Tooltip("Save as Scenario Template"):
            solara.Button(
                icon_name="mdi-content-save",
                on_click=lambda: set_show_save(True),
                icon=True,
                small=True,
            )

        # Save Dialog
        with solara.v.Dialog(v_model=show_save, max_width=400):
            with solara.Card(title="Save Scenario"):
                solara.InputText(
                    label="Filename", value=save_name, on_value=set_save_name
                )
                with solara.Row(justify="end"):
                    solara.Button(
                        "Cancel", on_click=lambda: set_show_save(False), text=True
                    )
                    solara.Button("Save", on_click=perform_save, color="primary")


@solara.component
def RunHistoryList():
    if not manager.run_history.value:
        solara.Markdown("_No runs yet._")
        return

    # Compact list with custom items
    with solara.Column(gap="4px"):
        for run in manager.run_history.value:
            is_selected = (manager.selected_run.value is not None) and (
                manager.selected_run.value.id == run.id
            )
            RunHistoryItem(run, is_selected)


@solara.component
def RunGraphs(compliance_series, price_series):
    """Reusable component for displaying run metrics graphs."""
    with solara.Columns([1, 1]):
        with solara.Column():
            if compliance_series:
                fig = _create_time_series_figure(
                    compliance_series, "Compliance", "green", ylim=(-0.05, 1.05)
                )
                solara.FigureMatplotlib(fig)
            else:
                solara.Markdown("No Data")

        with solara.Column():
            if price_series:
                fig = _create_time_series_figure(price_series, "Price", "blue")
                solara.FigureMatplotlib(fig)
            else:
                solara.Markdown("No Data")


def _create_time_series_figure(data, label, color, ylim=None):
    from matplotlib.figure import Figure

    fig = Figure(figsize=(6, 3))
    ax = fig.subplots()
    ax.plot(data, label=label, color=color)
    if ylim:
        ax.set_ylim(ylim)
    ax.legend()
    ax.grid(True)
    return fig


@solara.component
def Dashboard():
    # Helper to get data source
    run = manager.selected_run.value
    is_live = run is None

    # Extract data
    step_count = manager.step_count.value if is_live else len(run.steps)

    price_series = (
        manager.price_history.value
        if is_live
        else [s.market.get("price", 0) for s in run.steps]
    )

    # Placeholder for compliance in history (if missed in schema)
    if not is_live:
        # Calculate compliance per step dynamically
        compliance_series = []
        for s in run.steps:
            compliant_count = sum(1 for a in s.agents if a.get("Compliant"))
            total = len(s.agents)
            compliance_series.append(compliant_count / total if total > 0 else 0)
    else:
        compliance_series = manager.compliance_history.value

    # Split Dashboard Logic
    if not is_live:
        solara.Markdown("### Run Analysis")
        with solara.Row():
            # Left: Locked Params
            with solara.Column(style=("width: 40%; padding-right: 20px;")):
                with solara.Card("Run Configuration"):
                    ParamView(run.config)

            # Right: Results
            with solara.Column(style="width: 60%; padding-left: 20px;"):
                with solara.Card("Run Results"):
                    # Reuse the metrics display logic here or inline it
                    solara.Markdown(f"**Steps Taken:** {step_count}")

                    current_compliance = "N/A"
                    current_price = "N/A"
                    if compliance_series:
                        current_compliance = f"{compliance_series[-1]:.2%}"
                    if price_series:
                        current_price = f"{price_series[-1]:.2f}"

                    with solara.Columns([1, 1]):
                        solara.Markdown(f"**Final Compliance:** {current_compliance}")
                        solara.Markdown(f"**Final Price:** {current_price}")

        # Graphs (Full Width Bottom)
        with solara.Card("Run Graphs"):
            RunGraphs(compliance_series, price_series)

    else:
        # Live Monitoring View
        with solara.Card("Live Metrics"):
            solara.Markdown(f"**Step:** {step_count}")
            if compliance_series:
                solara.Markdown(f"**Current Compliance:** {compliance_series[-1]:.2%}")
            if price_series:
                solara.Markdown(f"**Current Price:** {price_series[-1]:.2f}")

        # Live Graphs
        RunGraphs(compliance_series, price_series)


@solara.component
def InspectorTab():
    run = manager.selected_run.value
    _ = manager.step_count.value  # Force dependency on step count
    is_live = run is None

    # Hook must be unconditional.
    # We use a key to reset state when the run ID changes.
    run_id = run.id if run else "live"
    step_idx, set_step_idx = solara.use_state(0, key=run_id)

    solara.Markdown(
        "### Step Inspector" + (" (Historical)" if not is_live else " (Live)")
    )

    # Flatten logic
    if is_live:
        price = manager.model.value.market.current_price if manager.model.value else 0
        supply = manager.model.value.market.max_supply if manager.model.value else 0
        # n_agents (Unused)
        agents_df = manager.agents_df.value
    else:
        # For history, use slider
        if len(run.steps) > 0:
            # Clamp
            idx = max(0, min(step_idx, len(run.steps) - 1))
            step = run.steps[idx]

            solara.SliderInt(
                label="Step View",
                value=step_idx,
                min=0,
                max=len(run.steps) - 1,
                on_value=set_step_idx,
            )

            price = step.market.get("price", 0)
            supply = step.market.get("supply", 0)
            # n_agents (Unused)
            agents_df = pd.DataFrame(step.agents)
        else:
            price = 0
            supply = 0
            agents_df = None

    # Use existing components for display
    # Market Summary
    # Use existing components for display
    # Market Summary
    with solara.Card("General"):
        solara.Markdown(f"**Clearing Price:** {price:.2f}")
        solara.Markdown(f"**Permits Available:** {supply:.2f} (Total Allowance)")

    # Agent Inspection
    if agents_df is not None:
        solara.Markdown("#### Quantitative Risk Analysis")

        with solara.Columns([1, 1]):
            with solara.Column():
                solara.Markdown("**True vs Reported Risk**")
                QuantitativeScatterPlot(agents_df)

            with solara.Column():
                solara.Markdown("**Agent Details**")
                # Show table but maybe select specific columns to avoid clutter
                # We want: ID, Capability, Allowance, True, Reported, Compliant?
                cols = [
                    "ID",
                    "Value",
                    "Net_Value",
                    "Capability",
                    # "Allowance",  # Removed from model
                    "True_Compute",
                    "Reported_Compute",
                    "Compliant",
                    "Audited",
                    "Caught",
                    "Penalty",
                    "Wealth",
                ]
                # Filter cols if they exist
                if agents_df is not None and not agents_df.empty:
                    valid_cols = [c for c in cols if c in agents_df.columns]
                    solara.DataFrame(agents_df[valid_cols], items_per_page=10)
                else:
                    solara.Markdown("No agent data available for this step.")
    else:
        solara.Markdown("No agent data.")


@solara.component
def ConfigPanel():
    # Scenario Selection (New File-based)
    show_load, set_show_load = solara.use_state(False)
    selected_file, set_selected_file = solara.use_state(None)

    def open_load_dialog():
        manager.refresh_scenarios()
        set_show_load(True)

    def do_load():
        if selected_file:
            manager.load_from_file(selected_file)
            set_show_load(False)

    with solara.Row(style="align-items: center;", justify="space-between"):
        solara.Markdown("### Configuration")
        solara.Button(
            "Load Scenario",
            on_click=open_load_dialog,
            icon_name="mdi-folder-open",
            small=True,
        )

    with solara.v.Dialog(v_model=show_load, max_width=400):
        with solara.Card(title="Load Scenario Template"):
            if manager.available_scenarios.value:
                solara.Select(
                    label="Choose File",
                    values=manager.available_scenarios.value,
                    value=selected_file,
                    on_value=set_selected_file,
                )
            else:
                solara.Markdown("_No scenarios found in scenarios/_")

            with solara.Row(justify="end", style="margin-top: 10px;"):
                solara.Button(
                    "Cancel", on_click=lambda: set_show_load(False), text=True
                )
                solara.Button(
                    "Load",
                    on_click=do_load,
                    color="primary",
                    disabled=(not selected_file),
                )

    # Old Selector (Legacy?) - optionally keep or remove. User asked for Load Button.
    # Removing old selector to clean up UI as requested ("load button... with popup")

    # Live Config controls (Always enabled now)
    # Removing 'disabled' logic and Restore buttons.

    with solara.lab.Tabs():
        with solara.lab.Tab("General"):
            solara.Markdown("**Simulation Parameters**")
            solara.InputInt(label="Steps", value=manager.steps)
            solara.InputInt(label="N Agents", value=manager.n_agents)
            solara.InputFloat(label="Token Cap (Q)", value=manager.token_cap)

        with solara.lab.Tab("Audit"):
            solara.Markdown("**Governor (Audit) Policy**")
            solara.InputFloat(label="Penalty Amount", value=manager.penalty)
            solara.InputFloat(label="Base Prob (pi_0)", value=manager.base_prob)
            solara.InputFloat(label="High Prob (pi_1)", value=manager.high_prob)
            solara.InputFloat(label="Signal TPR", value=manager.signal_tpr)
            solara.InputFloat(label="Signal FPR", value=manager.signal_fpr)

        with solara.lab.Tab("Lab"):
            solara.Markdown("**Lab Agent Generation**")
            RangeController(
                "Gross Value Range", manager.gross_value_min, manager.gross_value_max
            )
            RangeController(
                "Risk Profile Range", manager.risk_profile_min, manager.risk_profile_max
            )
            solara.InputFloat(
                label="Capability Value (V_b)", value=manager.capability_value
            )
            solara.InputFloat(label="Racing Factor (c_r)", value=manager.racing_factor)
            solara.InputFloat(
                label="Reputation Sensitivity", value=manager.reputation_sensitivity
            )
            solara.InputFloat(
                label="Audit Coefficient", value=manager.audit_coefficient
            )

    solara.Markdown("---")
    with solara.Row():
        solara.Button("Reset", on_click=manager.reset_model, color="error")
        # Hiding Step button for batch-mode feel, or keep it?
        # User said "when run is done... auto load".
        # Keeping manual Step is useful for debugging, but maybe de-emphasize?
        # Leaving it for now as "Advanced".
        solara.Button(
            "Step",
            on_click=manager.step,
            disabled=manager.is_playing.value,
        )

    solara.Button(
        label="Pause" if manager.is_playing.value else "Play",
        on_click=lambda: manager.is_playing.set(not manager.is_playing.value),
        color="primary",
    )


@solara.component
def EmptyState():
    with solara.Column(
        style="height: 60vh; justify-content: center; align-items: center; color: #888;"
    ):
        # Using a large icon and clear CTA
        solara.Markdown("## Ready to Simulate")
        solara.Markdown("Configure parameters on the left and click **Play**.")


@solara.component
def LoadingState():
    with solara.Column(
        style="height: 60vh; justify-content: center; align-items: center;"
    ):
        solara.v.ProgressCircular(indeterminate=True, color="primary", size=50)
        solara.Text("Simulating Scenario...", classes=["mt-4", "text-xl", "font-bold"])


@solara.component
def Page():
    # Inject CSS
    solara.Style(DENSITY_CSS)

    # Initialize if needed
    if manager.model.value is None:
        manager.reset_model()

    # Mount the controller (handles the loop)
    SimulationController()

    with solara.Sidebar():
        ConfigPanel()
        solara.Markdown("---")
        # RunHistoryList moved to main page

    solara.Title("Compute Permit Market Simulator")

    # --- Right Pane State Machine ---
    has_data = (manager.step_count.value > 0) or (
        manager.selected_run.value is not None
    )
    is_playing = manager.is_playing.value

    if is_playing:
        LoadingState()
    elif not has_data:
        EmptyState()
    else:
        with solara.lab.Tabs():
            with solara.lab.Tab("Summary"):
                Dashboard()
            with solara.lab.Tab("Details"):
                InspectorTab()

    # Run History at the bottom
    solara.Markdown("---")
    with solara.v.ExpansionPanels():
        with solara.v.ExpansionPanel():
            with solara.v.ExpansionPanelHeader():
                solara.Text("Previous Runs")
            with solara.v.ExpansionPanelContent():
                RunHistoryList()
