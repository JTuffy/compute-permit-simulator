import logging
from pathlib import Path

import pandas as pd
import solara
import solara.lab

from compute_permit_sim.core.constants import CHART_COLOR_MAP

from compute_permit_sim.services.config_manager import save_scenario
from compute_permit_sim.services.simulation import engine
from compute_permit_sim.vis.components import (
    AuditTargetingPlot,
    LabDecisionPlot,
    PayoffByStrategyPlot,
    QuantitativeScatterPlot,
    RangeController,
    RangeView,
    WealthDivergencePlot,
)
from compute_permit_sim.vis.state.active import active_sim
from compute_permit_sim.vis.state.config import ui_config
from compute_permit_sim.vis.state.history import session_history

# --- Logging Configuration ---
# Force configuration of the library logger to ensure we capture output
logger = logging.getLogger("compute_permit_sim")
logger.setLevel(logging.INFO)
# Clear existing handlers to avoid duplicates
if logger.handlers:
    logger.handlers.clear()

file_handler = logging.FileHandler("outputs/simulation.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Research Lab Design System CSS
# Research Lab Design System CSS - Moved to assets/style.css

# --- Components ---


@solara.component
def SimulationController():
    """Invisible component to handle the play loop."""
    # Using raise_error=False to gracefully handle Python 3.13 asyncio race conditions
    solara.lab.use_task(
        engine.play_loop,
        dependencies=[active_sim.is_playing.value],
        raise_error=False,
    )
    return solara.Div(style="display: none;")


@solara.component
def MetricCard(label: str, value: str, color_variant: str = "primary"):
    """Display a primary metric with visual hierarchy."""
    # Custom compact styling via CSS classes or inline style
    style = "padding: 12px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); background-color: white;"
    border = (
        "4px solid #1976D2"
        if color_variant == "primary"
        else "4px solid #4CAF50"
        if color_variant == "success"
        else "4px solid #FF9800"
    )

    with solara.Column(style=f"{style} border-left: {border}; margin: 4px;"):
        solara.HTML(
            tag="div",
            style="font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px;",
            unsafe_innerHTML=label,
        )
        solara.HTML(
            tag="div",
            style="font-size: 1.8rem; font-weight: 500;",
            unsafe_innerHTML=value,
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
def RunHistoryItem(run, is_selected):
    """Individual item in the history list."""

    # Label generation
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

    # Info Button (Mini-Dialog)
    # We use v.Btn directly for better slot compatibility if needed,
    # but simplest Solara pattern for hover menu is providing the activator slot content.
    # We will use the v_slots argument pattern which is most robust for raw v.Menu integration in Python.

    # However, Solara's v.Menu wraps the child content.
    # Let's try the safest "Manual Hover" state pattern if v.Menu activator fails.
    # Actually, using solara.v.Btn with slot='activator' AND passing `v_on='x.on'` is the raw way.
    # But Solara's JSX abstraction hides `x`.
    # Let's use `solara.v.Menu(v_slots=[{'name': 'activator', 'children': [btn]}])` logic manually?
    # No, that's messy.

    # Let's go with a Clickable Info Button (simpler interaction model) that toggles the menu.
    # User asked for hover, but if it's broken, a working click is better.
    # Wait, we can use `solara.lab.Menu`? No.

    # Let's try `solara.v.Tooltip` with `bottom=True` containing the Rich Text?
    # Vuetify tooltips only take text/html.

    # Let's try the `solara.v.Btn` with `slot='activator'` again but verify imports.
    # The previous error was `solara.v.Template`.
    # The symptom "nothing happens" suggests the slot isn't being picked up or events aren't bound.

    # Let's try explicit `v_on` binding if possible? No.

    # REVISED STRATEGY: Use `solara.v.Menu` with a button relying on `v_model` (open state).
    # We simulate hover using `on_mouse_enter`.

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
                    solara.Text(f"Run: {run.id}")

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

                    # Metrics (if available)
                    if run.metrics:
                        solara.HTML(
                            tag="h4",
                            unsafe_innerHTML="Results",
                            style="margin: 16px 0 8px 0; border-bottom: 1px solid #eee; padding-bottom: 4px;",
                        )
                        with solara.Columns([1, 1]):
                            if "final_compliance" in run.metrics:
                                solara.Markdown(
                                    f"**Final Compliance:** {run.metrics['final_compliance']:.1%}"
                                )
                            if "final_price" in run.metrics:
                                solara.Markdown(
                                    f"**Final Price:** ${run.metrics['final_price']:.2f}"
                                )
                            if "fraud_detected" in run.metrics:
                                solara.Markdown(
                                    f"**Fraud Detected:** {run.metrics['fraud_detected']}"
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

        # Excel Export - synchronous to avoid numpy import issues in threads
        def export_excel():
            from compute_permit_sim.vis.excel_export import export_run_to_excel

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


@solara.component
def RunGraphs(compliance_series, price_series, wealth_series):
    """Reusable component for displaying run metrics graphs."""
    with solara.Columns([1, 1, 1]):
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

        with solara.Column():
            if wealth_series and wealth_series[0]:
                WealthDivergencePlot(*wealth_series)
            else:
                solara.Markdown("No Wealth Data")


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
    color_map = CHART_COLOR_MAP
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
def AnalysisPanel():
    """Unified analysis panel combining metrics, timeline, graphs, and agent table.

    Renders consistently regardless of live vs historical mode by using a
    unified data access pattern at the top.
    """
    # --- Unified Data Access ---
    run = session_history.selected_run.value
    is_live = run is None

    # Force dependency on step count for live updates
    _ = active_sim.step_count.value

    # Step index state for historical timeline (hoisted to ensure consistent hook calls)
    run_id = run.id if run else "live"
    step_idx, set_step_idx = solara.use_state(0, key=run_id)

    # --- Memoized time series (only recompute when run changes, not on slider move) ---
    def compute_time_series():
        if is_live:
            return (
                active_sim.compliance_history.value,
                active_sim.price_history.value,
                (
                    active_sim.wealth_history_compliant.value,
                    active_sim.wealth_history_non_compliant.value,
                ),
            )
        elif run and run.steps:
            compliance = []
            prices = []
            w_comp = []
            w_non = []
            for s in run.steps:
                # Compliance & Price
                compliant_count = sum(1 for a in s.agents if a.is_compliant)
                total = len(s.agents)
                compliance.append(compliant_count / total if total > 0 else 0)
                prices.append(s.market.get("price", 0))

                # Wealth
                w_comp.append(
                    sum(a.wealth for a in s.agents if a.is_compliant)
                )  # AgentSnapshot has wealth
                w_non.append(sum(a.wealth for a in s.agents if not a.is_compliant))

            return compliance, prices, (w_comp, w_non)
        return [], [], ([], [])

    compliance_series, price_series, wealth_series = solara.use_memo(
        compute_time_series,
        dependencies=[run_id, active_sim.step_count.value if is_live else 0],
    )

    # --- Extract step-specific data ---
    if is_live:
        step_count = active_sim.step_count.value
        agents_df = active_sim.agents_df.value
        market_price = (
            active_sim.model.value.market.current_price if active_sim.model.value else 0
        )
        market_supply = (
            active_sim.model.value.market.max_supply if active_sim.model.value else 0
        )

        # Determine config for display
        # We need to construct a display-friendly object that mirrors the structure of SimulationConfig
        from types import SimpleNamespace

        # Helpers for nested structure
        market_c = SimpleNamespace(token_cap=ui_config.token_cap.value)
        audit_c = SimpleNamespace(
            base_prob=ui_config.base_prob.value,
            high_prob=ui_config.high_prob.value,
            penalty_amount=ui_config.penalty.value,
            false_negative_rate=1.0 - ui_config.signal_tpr.value,
            false_positive_rate=ui_config.signal_fpr.value,
        )
        lab_c = SimpleNamespace(
            racing_factor=ui_config.racing_factor.value,
            capability_value=ui_config.capability_value.value,
            reputation_sensitivity=ui_config.reputation_sensitivity.value,
            audit_coefficient=ui_config.audit_coefficient.value,
        )

        config = SimpleNamespace(
            steps=ui_config.steps.value,
            n_agents=ui_config.n_agents.value,
            market=market_c,
            audit=audit_c,
            lab=lab_c,
        )

    else:
        step_count = len(run.steps) if run else 0

        # Get step-specific data based on slider (not memoized - changes with slider)
        if run and len(run.steps) > 0:
            idx = max(0, min(step_idx, len(run.steps) - 1))
            total_steps = len(run.steps) - 1
            step = run.steps[idx]
            market_price = step.market.get("price", 0)
            market_supply = step.market.get("supply", 0)
            agents_df = pd.DataFrame([a.model_dump() for a in step.agents])
        else:
            idx = 0
            total_steps = 0
            market_price = 0
            market_supply = 0
            agents_df = None

        config = run.config if run else None

    # --- Compute derived values ---
    current_compliance = "N/A"
    comp_color = "primary"
    if compliance_series:
        comp_val = compliance_series[-1]
        current_compliance = f"{comp_val:.1%}"
        comp_color = "success" if comp_val >= 0.8 else "warning"

    current_price = f"${price_series[-1]:.2f}" if price_series else "N/A"

    # --- Render Unified Layout ---
    with solara.Column(classes=["analysis-panel"]):
        # SECTION 1: Key Metrics
        with solara.Card("Key Metrics"):
            with solara.Columns([1, 1, 1]):
                MetricCard("Steps Completed", f"{step_count}", "primary")
                MetricCard("Compliance Rate", current_compliance, comp_color)
                MetricCard("Market Price", current_price, "primary")

        # SECTION 2: Run Configuration (Historical Only)
        # SECTION 2: Run Configuration (Historical Only)
        if config is not None:
            with solara.Card():
                with solara.Details("Run Configuration", expand=False):
                    c = config
                    with solara.lab.Tabs():
                        with solara.lab.Tab("General"):
                            with solara.Columns([1, 1]):
                                with solara.Column():
                                    solara.Markdown(f"**Steps:** {c.steps}")
                                    solara.Markdown(f"**Agents:** {c.n_agents}")
                                with solara.Column():
                                    solara.Markdown(
                                        f"**Token Cap:** {int(c.market.token_cap)}"
                                    )

                        with solara.lab.Tab("Audit Policy"):
                            with solara.Columns([1, 1]):
                                with solara.Column():
                                    solara.Markdown(
                                        f"**Base π₀:** {c.audit.base_prob:.2%}"
                                    )
                                    solara.Markdown(
                                        f"**High π₁:** {c.audit.high_prob:.2%}"
                                    )
                                    solara.Markdown(
                                        f"**Penalty:** ${c.audit.penalty_amount:.0f}"
                                    )
                                with solara.Column():
                                    solara.Markdown(
                                        f"**TPR:** {1 - c.audit.false_negative_rate:.2%}"
                                    )
                                    solara.Markdown(
                                        f"**FPR:** {c.audit.false_positive_rate:.2%}"
                                    )

                        with solara.lab.Tab("Lab Dynamics"):
                            with solara.Columns([1, 1]):
                                with solara.Column():
                                    solara.Markdown(
                                        f"**Racing cr:** {c.lab.racing_factor:.2f}"
                                    )
                                    solara.Markdown(
                                        f"**Capability Vb:** {c.lab.capability_value:.2f}"
                                    )
                                with solara.Column():
                                    solara.Markdown(
                                        f"**Reputation β:** {c.lab.reputation_sensitivity:.2f}"
                                    )
                                    solara.Markdown(
                                        f"**Audit Coeff:** {c.lab.audit_coefficient:.2f}"
                                    )

        # SECTION 3: Time Series Graphs
        with solara.Card("Time Series Analysis"):
            RunGraphs(compliance_series, price_series, wealth_series)

        # SECTION 4: Timeline Slider (Historical Only) - grouped with step-specific content
        if not is_live and len(run.steps) > 0:
            with solara.Card("Step Inspector"):
                with solara.Column(align="center"):
                    solara.v.Slider(
                        v_model=idx,
                        on_v_model=set_step_idx,
                        min=0,
                        max=total_steps,
                        step=1,
                        track_color="grey lighten-2",
                        track_fill_color="primary",
                        thumb_label="always",
                        thumb_size=24,
                        color="primary",
                        style_="width: 100%; max-width: 800px;",
                    )
                # Market summary for selected step
                solara.Markdown(
                    f"**Step {idx + 1}** — Clearing Price: ${market_price:.2f} | "
                    f"Permits: {market_supply:.0f}"
                )

        # SECTION 5: Step Analysis (Agent Graphs)
        # SECTION 5: Step Analysis (Agent Graphs)
        if agents_df is not None and not agents_df.empty:
            with solara.Card("Step Analysis"):
                with solara.Columns([1, 1, 1]):
                    with solara.Column():
                        # Determine efficient detection p and penalty
                        if is_live:
                            # Live mode: use reactive UI config
                            p_eff = ui_config.high_prob.value
                            penalty = ui_config.penalty.value
                        elif config:
                            # History mode: use stored config
                            p_eff = config.audit.high_prob
                            penalty = config.audit.penalty_amount
                        else:
                            p_eff = 0
                            penalty = 0

                        if p_eff > 0:
                            LabDecisionPlot(agents_df, p_eff, penalty)
                        else:
                            solara.Markdown("Deterrence Frontier (No Config)")
                    with solara.Column():
                        AuditTargetingPlot(agents_df)
                    with solara.Column():
                        PayoffByStrategyPlot(agents_df)

                # Optional secondary row - Enforce 3-column grid consistency
                with solara.Columns([1, 1, 1]):
                    with solara.Column():
                        QuantitativeScatterPlot(agents_df)
                    with solara.Column():
                        pass  # Empty placeholder for alignment
                    with solara.Column():
                        pass  # Empty placeholder for alignment

            # SECTION 6: Agent Details Table
            with solara.Card("Agent Details"):
                cols = [
                    "id",
                    "capacity",
                    "has_permit",
                    "used_compute",
                    "reported_compute",
                    "is_compliant",
                    "was_audited",
                    "was_caught",
                    "penalty_amount",
                    "revenue",
                    "step_profit",
                    "wealth",
                ]
                valid_cols = [c for c in cols if c in agents_df.columns]
                solara.DataFrame(agents_df[valid_cols], items_per_page=15)
        else:
            with solara.Card("Agent Details"):
                solara.Markdown("No agent data available for this step.")


@solara.component
def ConfigPanel():
    # Wrap entire panel in compact styling
    with solara.Column(classes=["sidebar-compact"]):
        # Scenario Selection (New File-based)
        show_load, set_show_load = solara.use_state(False)
        selected_file, set_selected_file = solara.use_state(None)

        def open_load_dialog():
            session_history.refresh_scenarios()
            set_show_load(True)

        def do_load():
            if selected_file:
                engine.load_scenario(selected_file)
                set_show_load(False)

        # Header with Load and Play buttons
        with solara.Row(
            style="align-items: center; margin-bottom: 8px;", justify="space-between"
        ):
            solara.Markdown("**SCENARIO**", style="font-size: 0.9rem; opacity: 0.7;")
            with solara.Row():
                solara.Button(
                    icon_name="mdi-play"
                    if not active_sim.is_playing.value
                    else "mdi-pause",
                    on_click=lambda: active_sim.is_playing.set(
                        not active_sim.is_playing.value
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

        # Load Dialog - using v.Card for proper sizing
        with solara.v.Dialog(
            v_model=show_load,
            on_v_model=set_show_load,
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
            with solara.Column():
                solara.InputInt(label="Steps", value=ui_config.steps, dense=True)
                solara.InputInt(label="N Agents", value=ui_config.n_agents, dense=True)
                solara.InputFloat(
                    label="Token Cap Q", value=ui_config.token_cap, dense=True
                )

        # Audit Policy Card
        with solara.Card("Audit Policy", style="margin-bottom: 6px;"):
            with solara.Column():
                solara.InputFloat(
                    label="Penalty $", value=ui_config.penalty, dense=True
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
                solara.InputFloat(
                    label="Capability Vb", value=ui_config.capability_value, dense=True
                )
                solara.InputFloat(
                    label="Racing cr", value=ui_config.racing_factor, dense=True
                )
                solara.InputFloat(
                    label="Reputation β",
                    value=ui_config.reputation_sensitivity,
                    dense=True,
                )
                solara.InputFloat(
                    label="Audit Coeff", value=ui_config.audit_coefficient, dense=True
                )

        # Action Buttons Section
        solara.Markdown("---")
        # Primary action: Play/Pause (prominent)
        solara.Button(
            label="⏸ Pause" if active_sim.is_playing.value else "▶ Play",
            on_click=lambda: active_sim.is_playing.set(not active_sim.is_playing.value),
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
    solara.Style(Path(__file__).parent / "assets" / "style.css")

    # Initialize if needed
    if active_sim.model.value is None:
        engine.reset_model()

    # Mount the controller (handles the loop)
    SimulationController()

    with solara.Sidebar():
        ConfigPanel()

    solara.Title("Compute Permit Market Simulator")

    # --- Right Pane State Machine ---
    has_data = (active_sim.step_count.value > 0) or (
        session_history.selected_run.value is not None
    )
    is_playing = active_sim.is_playing.value

    if is_playing:
        LoadingState()
    elif not has_data:
        EmptyState()
    else:
        # Unified analysis view (no tabs)
        AnalysisPanel()
