"""Agent details table — per-step agent data view.

Computes agents_df from steps + step_idx internally so that Solara's
scalar integer prop-change detection drives reactivity reliably.
"""

from __future__ import annotations

import pandas as pd
import solara

from compute_permit_sim.schemas.columns import ColumnNames


@solara.component
def AgentDetailsTable(
    steps: list | None = None,
    step_idx: int = 0,
    live_agents_df: pd.DataFrame | None = None,
    is_live: bool = False,
) -> None:
    """Tabular view of all agent fields for the selected step.

    Uses ``step_idx`` (scalar) as the reactive prop to drive re-renders on
    slider changes. ``agents_df`` is computed here, not passed as a prop.
    """
    agents_df: pd.DataFrame | None = None

    if is_live:
        agents_df = live_agents_df
    elif steps and len(steps) > 0:
        idx = max(0, min(step_idx, len(steps) - 1))
        step = steps[idx]
        agents_df = pd.DataFrame([a.model_dump() for a in step.agents])

    if agents_df is not None and not agents_df.empty:
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
            solara.Markdown("*No agent data available for this step.*")
