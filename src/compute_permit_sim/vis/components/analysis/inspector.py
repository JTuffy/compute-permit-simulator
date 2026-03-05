"""Step inspector component — slider and per-step agent analysis."""

import solara

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.vis.components.factories import ChartFactory


@solara.component
def StepInspector(
    is_live: bool,
    run,
    step_idx: int,
    set_step_idx,
    market_price: float,
    market_supply: float,
    agents_df,
):
    """Component for inspecting details of a specific simulation step."""
    # Timeline Slider (Historical Only)
    if not is_live and run and len(run.steps) > 0:
        with solara.Card("Step Inspector"):
            solara.SliderInt(
                label="Step",
                value=step_idx,
                on_value=set_step_idx,
                min=0,
                max=len(run.steps) - 1,
                thumb_label="always",
            )
            solara.Markdown(
                f"**Step {step_idx + 1}** — Clearing Price: ${market_price:.2f} | "
                f"Permits: {market_supply:.0f}"
            )

    # Step Analysis (Agent Graphs)
    if agents_df is not None and not agents_df.empty:
        with solara.Card("Step Analysis"):
            # Row 1: Risk Analysis (scatter, audit targeting, compliance distribution)
            ChartFactory.render_risk_analysis(agents_df)

        # Agent Details Table
        with solara.Card("Agent Details"):
            cols = [
                ColumnNames.ID,
                ColumnNames.COMPUTE_CAPACITY,
                ColumnNames.PLANNED_TRAINING_FLOPS,
                ColumnNames.USED_TRAINING_FLOPS,
                ColumnNames.REPORTED_TRAINING_FLOPS,
                ColumnNames.HAS_PERMIT,
                ColumnNames.IS_COMPLIANT,
                ColumnNames.WAS_AUDITED,
                ColumnNames.WAS_CAUGHT,
                ColumnNames.CAUGHT_SOURCE,
                ColumnNames.PENALTY_AMOUNT,
                ColumnNames.ECONOMIC_VALUE,
                ColumnNames.BID_PRICE,
                ColumnNames.PERMITS_WANTED,
                ColumnNames.AUDIT_COEFFICIENT,
                ColumnNames.CUMULATIVE_CAPABILITY,
            ]
            valid_cols = [c for c in cols if c in agents_df.columns]
            solara.DataFrame(agents_df[valid_cols], items_per_page=15)
    else:
        with solara.Card("Agent Details"):
            solara.Markdown("No agent data available for this step.")
