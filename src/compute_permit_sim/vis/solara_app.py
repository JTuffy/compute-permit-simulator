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

# Research Lab Design System CSS
DENSITY_CSS = """
/* Hide Solara watermark */
footer { display: none !important; }

/* Color Palette - Research Lab Theme */
:root {
  --lab-primary: #2196F3;
  --lab-success: #4CAF50;
  --lab-warning: #FF9800;
  --lab-error: #F44336;
  --lab-input-bg: #F5F7FA;
  --lab-output-bg: #FFFFFF;
  --lab-metric-bg: #E3F2FD;
  --lab-spacing-tight: 4px;
  --lab-spacing-normal: 8px;
  --lab-spacing-loose: 16px;
}

/* Left Panel: Compact Control Panel Style */
.sidebar-compact .v-card { 
  margin-bottom: 8px !important; 
  background: var(--lab-input-bg) !important;
  border-radius: 4px !important;
}

.sidebar-compact .v-input { 
  margin-bottom: 2px !important; 
  font-size: 0.85rem !important;
}

.sidebar-compact .v-card__text { 
  padding: 6px 10px !important; 
}

.sidebar-compact .v-card__title { 
  font-size: 0.75rem !important; 
  text-transform: uppercase !important; 
  letter-spacing: 0.5px !important; 
  opacity: 0.7 !important;
  padding: 6px 10px !important;
  font-weight: 600 !important;
}

.sidebar-compact .v-label {
  font-size: 0.85rem !important;
}

/* Compact tab styling */
.sidebar-compact .v-tab {
  font-size: 0.8rem !important;
  min-width: 60px !important;
  padding: 0 8px !important;
}

/* Right Panel: Spacious Analytical Readout */
.analysis-panel { 
  padding: 24px !important; 
}

.analysis-panel .v-card {
  margin-bottom: 20px !important;
}

.analysis-panel .v-card__title {
  font-size: 1.1rem !important;
  padding: 12px 16px !important;
  font-weight: 600 !important;
}

.analysis-panel .v-card__text {
  padding: 16px !important;
}

/* Metric Cards */
.metric-card { 
  padding: 8px 12px !important; 
  background: var(--lab-metric-bg) !important;
  border-left: 3px solid var(--lab-primary) !important;
  border-radius: 4px !important;
  margin-bottom: 8px !important;
}

.metric-card.success { 
  border-left-color: var(--lab-success) !important; 
  background: #E8F5E9 !important;
}

.metric-card.warning { 
  border-left-color: var(--lab-warning) !important; 
  background: #FFF3E0 !important;
}

.metric-value { 
  font-size: 1.4rem !important; 
  font-family: 'Roboto Mono', monospace !important; 
  font-weight: 700 !important;
  line-height: 1.2 !important;
  margin-bottom: 2px !important;
}

.metric-label { 
  font-size: 0.65rem !important; 
  text-transform: uppercase !important; 
  letter-spacing: 0.5px !important; 
  opacity: 0.6 !important;
  font-weight: 600 !important;
}

/* Compact Run History */
.run-history-compact {
  max-height: 250px !important;
  overflow-y: auto !important;
  padding: 4px !important;
}

.run-history-compact .v-btn {
  font-size: 0.75rem !important;
  padding: 2px 6px !important;
}

/* General density improvements */
.v-application .v-input--dense .v-input__control {
  min-height: 32px !important;
}

.solara-markdown p { 
  margin-bottom: 4px !important; 
}

/* Button hierarchy */
.v-btn.v-btn--text {
  text-transform: none !important;
}

/* Numeric display */
.numeric-display {
  font-family: 'Roboto Mono', monospace !important;
  font-weight: 500 !important;
}
"""

# --- Components ---


@solara.component
def SimulationController():
    """Invisible component to handle the play loop."""
    solara.lab.use_task(manager.play_loop, dependencies=[manager.is_playing.value])
    return solara.Div(style="display: none;")


@solara.component
def MetricCard(label: str, value: str, color_variant: str = "primary"):
    """Display a primary metric with visual hierarchy.

    Args:
        label: Metric label (e.g., "Final Compliance")
        value: Formatted value (e.g., "87.5%")
        color_variant: "primary", "success", or "warning"
    """
    classes = ["metric-card"]
    if color_variant != "primary":
        classes.append(color_variant)

    with solara.Card(classes=classes):
        solara.HTML(
            tag="div",
            unsafe_innerHTML=f"""
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            """,
        )


@solara.component
def ScenarioCard(title: str):
    """Compact card for scenario configuration sections.

    Args:
        title: Section title (e.g., "General", "Audit Policy")
    """
    # This is a wrapper that children can be placed in
    # Using context manager pattern
    pass


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
        with solara.v.Dialog(v_model=show_save, max_width=500):
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
    """Create publication-quality time series figure.

    Args:
        data: Time series data
        label: Series label
        color: Line color (can be 'green', 'blue', etc.)
        ylim: Optional y-axis limits

    Returns:
        Matplotlib figure
    """
    from matplotlib.figure import Figure

    # Color mapping for research lab aesthetic
    color_map = {
        "green": "#4CAF50",
        "blue": "#2196F3",
        "red": "#F44336",
        "orange": "#FF9800",
    }
    plot_color = color_map.get(color, color)

    # Larger figure for better readability
    fig = Figure(figsize=(8, 4), dpi=100)
    ax = fig.subplots()

    # Plot with publication-quality styling
    ax.plot(data, label=label, color=plot_color, linewidth=2.5, alpha=0.9)

    # Enhanced grid
    ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.8)

    # Styling
    ax.set_xlabel("Step", fontsize=11, fontweight="500")
    ax.set_ylabel(label, fontsize=11, fontweight="500")
    ax.legend(loc="best", framealpha=0.9, fontsize=10)

    # Set ylim if provided
    if ylim:
        ax.set_ylim(ylim)

    # Cleaner spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.2)
    ax.spines["bottom"].set_linewidth(1.2)

    # Tighter layout
    fig.tight_layout()

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

    # Calculate compliance series
    if not is_live:
        compliance_series = []
        for s in run.steps:
            compliant_count = sum(1 for a in s.agents if a.get("Compliant"))
            total = len(s.agents)
            compliance_series.append(compliant_count / total if total > 0 else 0)
    else:
        compliance_series = manager.compliance_history.value

    # Wrap in analysis panel styling
    with solara.Column(classes=["analysis-panel"]):
        # Primary Metrics Section
        with solara.Card("Key Metrics"):
            # Get current values
            current_compliance = "N/A"
            current_price = "N/A"

            if compliance_series:
                comp_val = compliance_series[-1]
                current_compliance = f"{comp_val:.1%}"
                comp_color = "success" if comp_val >= 0.8 else "warning"
            else:
                comp_color = "primary"

            if price_series:
                current_price = f"${price_series[-1]:.2f}"

            # Display metrics in columns
            with solara.Columns([1, 1, 1]):
                MetricCard("Steps Completed", f"{step_count}", "primary")
                MetricCard("Compliance Rate", current_compliance, comp_color)
                MetricCard("Market Price", current_price, "primary")

        # Configuration Summary (if viewing historical run)
        if not is_live:
            with solara.Card("Run Configuration", style="background: #F5F7FA;"):
                c = run.config
                with solara.Columns([1, 1, 1, 1]):
                    with solara.Column():
                        solara.Markdown(f"**Steps:** {c.steps}")
                        solara.Markdown(f"**Agents:** {c.n_agents}")
                        solara.Markdown(f"**Token Cap:** {int(c.market.token_cap)}")
                    with solara.Column():
                        solara.Markdown(f"**Base π₀:** {c.audit.base_prob:.2%}")
                        solara.Markdown(f"**High π₁:** {c.audit.high_prob:.2%}")
                        solara.Markdown(f"**Penalty:** ${c.audit.penalty_amount:.0f}")
                    with solara.Column():
                        solara.Markdown(
                            f"**TPR:** {1 - c.audit.false_negative_rate:.2%}"
                        )
                        solara.Markdown(f"**FPR:** {c.audit.false_positive_rate:.2%}")
                        solara.Markdown(f"**Racing cr:** {c.lab.racing_factor:.2f}")
                    with solara.Column():
                        solara.Markdown(
                            f"**Capability Vb:** {c.lab.capability_value:.2f}"
                        )
                        solara.Markdown(
                            f"**Reputation β:** {c.lab.reputation_sensitivity:.2f}"
                        )
                        solara.Markdown(
                            f"**Audit Coeff:** {c.lab.audit_coefficient:.2f}"
                        )

        # Time Series Graphs - Publication Quality
        with solara.Card("Analysis"):
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

    solara.Markdown("### Inspect Step")

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
        # Graph Section - Constrained to 1/3 width on top
        with solara.Card("Quantitative Risk Analysis"):
            # Use 3 columns but only put graph in first one to constrain its size
            with solara.Columns([1, 2]):
                with solara.Column():
                    QuantitativeScatterPlot(agents_df)
                with solara.Column():
                    # Empty spacer
                    pass

        # Agent Details Table - Full width below
        with solara.Card("Agent Details"):
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
                solara.DataFrame(agents_df[valid_cols], items_per_page=15)
            else:
                solara.Markdown("No agent data available for this step.")
    else:
        solara.Markdown("No agent data.")


@solara.component
def ConfigPanel():
    # Wrap entire panel in compact styling
    with solara.Column(classes=["sidebar-compact"], gap="4px"):
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

        # Header with Load and Play buttons
        with solara.Row(
            style="align-items: center; margin-bottom: 8px;", justify="space-between"
        ):
            solara.Markdown("**SCENARIO**", style="font-size: 0.9rem; opacity: 0.7;")
            with solara.Row(gap="4px"):
                solara.Button(
                    icon_name="mdi-play"
                    if not manager.is_playing.value
                    else "mdi-pause",
                    on_click=lambda: manager.is_playing.set(
                        not manager.is_playing.value
                    ),
                    icon=True,
                    small=True,
                    color="primary",
                )
                solara.Button(
                    "Load",
                    on_click=open_load_dialog,
                    icon_name="mdi-folder-open",
                    small=True,
                    text=True,
                )

        with solara.v.Dialog(v_model=show_load, max_width=500):
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

        # General Parameters Card
        with solara.Card("General", style="margin-bottom: 6px;"):
            with solara.Column(gap="2px"):
                solara.InputInt(label="Steps", value=manager.steps, dense=True)
                solara.InputInt(label="N Agents", value=manager.n_agents, dense=True)
                solara.InputFloat(
                    label="Token Cap Q", value=manager.token_cap, dense=True
                )

        # Audit Policy Card
        with solara.Card("Audit Policy", style="margin-bottom: 6px;"):
            with solara.Column(gap="2px"):
                solara.InputFloat(label="Penalty $", value=manager.penalty, dense=True)
                solara.InputFloat(label="Base π₀", value=manager.base_prob, dense=True)
                solara.InputFloat(label="High π₁", value=manager.high_prob, dense=True)
                solara.InputFloat(
                    label="Signal TPR", value=manager.signal_tpr, dense=True
                )
                solara.InputFloat(
                    label="Signal FPR", value=manager.signal_fpr, dense=True
                )

        # Lab Generation Card
        with solara.Card("Lab Generation", style="margin-bottom: 6px;"):
            with solara.Column(gap="2px"):
                RangeController(
                    "Gross Value", manager.gross_value_min, manager.gross_value_max
                )
                RangeController(
                    "Risk Profile", manager.risk_profile_min, manager.risk_profile_max
                )
                solara.InputFloat(
                    label="Capability Vb", value=manager.capability_value, dense=True
                )
                solara.InputFloat(
                    label="Racing cr", value=manager.racing_factor, dense=True
                )
                solara.InputFloat(
                    label="Reputation β",
                    value=manager.reputation_sensitivity,
                    dense=True,
                )
                solara.InputFloat(
                    label="Audit Coeff", value=manager.audit_coefficient, dense=True
                )

        # Action Buttons Section
        solara.Markdown("---")
        # Primary action: Play/Pause (prominent)
        solara.Button(
            label="⏸ Pause" if manager.is_playing.value else "▶ Play",
            on_click=lambda: manager.is_playing.set(not manager.is_playing.value),
            color="primary",
            block=True,
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
