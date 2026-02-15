import solara

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.vis.components.factories import ChartFactory
from compute_permit_sim.vis.state.config import ui_config


@solara.component
def StepInspector(
    is_live: bool,
    run,
    step_idx: int,
    set_step_idx,
    market_price: float,
    market_supply: float,
    agents_df,
    config,
):
    """Component for inspecting details of a specific step."""
    # Timeline Slider (Historical Only)
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

    # Step Analysis (Agent Graphs)
    if agents_df is not None and not agents_df.empty:
        with solara.Card("Step Analysis"):
            # Row 1: Risk Analysis (Scatter, Targeting, Capacity)
            ChartFactory.render_risk_analysis(agents_df)

            # Row 2: Theoretical & Deep Dives
            # REFACTOR: Use ChartFactory for deterrence logic
            # Determine efficient detection p and penalty
            if is_live:
                p_eff = ui_config.high_prob.value
                penalty = ui_config.penalty_amount.value
            elif config:
                p_eff = config.audit.high_prob
                penalty = config.audit.penalty_amount
            else:
                p_eff = 0
                penalty = 0

            ChartFactory.render_deterrence_analysis(agents_df, p_eff, penalty)

        # Agent Details Table
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
