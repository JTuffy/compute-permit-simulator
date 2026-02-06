import pandas as pd
import solara

from compute_permit_sim.core.constants import ColumnNames
from compute_permit_sim.vis.components import (
    AuditTargetingPlot,
    CapacityUtilizationPlot,
    CheatingGainPlot,
    LabDecisionPlot,
    MetricCard,
    PayoffByStrategyPlot,
    QuantitativeScatterPlot,
    WealthDivergencePlot,
)
from compute_permit_sim.vis.plotting import plot_time_series
from compute_permit_sim.vis.state.active import active_sim
from compute_permit_sim.vis.state.config import ui_config
from compute_permit_sim.vis.state.history import session_history


@solara.component
def RunGraphs(
    compliance_series: pd.Series, price_series: pd.Series, wealth_series: pd.Series
) -> solara.Element:
    """Reusable component for displaying run metrics graphs."""
    with solara.Columns([1, 1, 1]):
        with solara.Column():
            if compliance_series:
                fig = plot_time_series(
                    compliance_series, "Compliance", "green", ylim=(-0.05, 1.05)
                )
                solara.FigureMatplotlib(fig)
            else:
                solara.Markdown("No Data")

        with solara.Column():
            if price_series:
                fig = plot_time_series(price_series, "Price", "blue")
                solara.FigureMatplotlib(fig)
            else:
                solara.Markdown("No Data")

        with solara.Column():
            if wealth_series and wealth_series[0]:
                WealthDivergencePlot(*wealth_series)
            else:
                solara.Markdown("No Wealth Data")


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
                prices.append(s.market.price)

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
        config = ui_config.to_scenario_config()

    else:
        step_count = len(run.steps) if run else 0

        # Get step-specific data based on slider (not memoized - changes with slider)
        if run and len(run.steps) > 0:
            idx = max(0, min(step_idx, len(run.steps) - 1))
            step = run.steps[idx]
            market_price = step.market.price
            market_supply = step.market.supply
            agents_df = pd.DataFrame([a.model_dump() for a in step.agents])
        else:
            idx = 0
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
            # Determine seed to display
            display_seed = "Random"
            if is_live:
                if active_sim.actual_seed.value is not None:
                    display_seed = str(active_sim.actual_seed.value)
            elif config and config.seed is not None:
                display_seed = str(config.seed)

            with solara.Columns([1, 1, 1, 1]):
                MetricCard("Steps", f"{step_count}", "primary")
                MetricCard("Compliance", current_compliance, comp_color)
                MetricCard("Price", current_price, "primary")
                MetricCard("Seed", display_seed, "secondary")

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

        # SECTION 4: Timeline Slider (Historical Only)
        if not is_live and run and len(run.steps) > 0:
            with solara.Card("Step Inspector"):
                # Use standard SliderInt
                solara.SliderInt(
                    label="Step",
                    value=step_idx,
                    on_value=set_step_idx,
                    min=0,
                    max=len(run.steps) - 1,
                    thumb_label="always",
                )
                # Market summary for selected step
                solara.Markdown(
                    f"**Step {step_idx + 1}** — Clearing Price: ${market_price:.2f} | "
                    f"Permits: {market_supply:.0f}"
                )

        # SECTION 5: Step Analysis (Agent Graphs)
        if agents_df is not None and not agents_df.empty:
            with solara.Card("Step Analysis"):
                with solara.Columns([1, 1, 1]):
                    with solara.Column():
                        # 1. Risk vs Reported
                        QuantitativeScatterPlot(agents_df)
                    with solara.Column():
                        # 2. Audit Targeting (Center)
                        AuditTargetingPlot(agents_df)
                    with solara.Column():
                        # 3. Payoff (Right)
                        PayoffByStrategyPlot(agents_df)

                # Row 2: Theoretical & Deep Dives
                with solara.Columns([1, 1, 1]):
                    with solara.Column():
                        # 4. Deterrence Frontier (Demoted)
                        # Determine efficient detection p and penalty
                        if is_live:
                            p_eff = ui_config.high_prob.value
                            penalty = ui_config.penalty.value
                        elif config:
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
                        # 5. Cheating Gain (New)
                        CheatingGainPlot(agents_df)
                    with solara.Column():
                        # 6. Capacity Utilization (New)
                        CapacityUtilizationPlot(agents_df)

            # SECTION 6: Agent Details Table
            with solara.Card("Agent Details"):
                cols = [
                    ColumnNames.ID,
                    ColumnNames.CAPACITY,
                    ColumnNames.HAS_PERMIT,
                    ColumnNames.USED_COMPUTE,
                    ColumnNames.REPORTED_COMPUTE,
                    ColumnNames.IS_COMPLIANT,
                    ColumnNames.WAS_AUDITED,
                    ColumnNames.WAS_CAUGHT,
                    ColumnNames.PENALTY_AMOUNT,
                    ColumnNames.REVENUE,
                    ColumnNames.STEP_PROFIT,
                    ColumnNames.WEALTH,
                ]
                valid_cols = [c for c in cols if c in agents_df.columns]
                solara.DataFrame(agents_df[valid_cols], items_per_page=15)
        else:
            with solara.Card("Agent Details"):
                solara.Markdown("No agent data available for this step.")
