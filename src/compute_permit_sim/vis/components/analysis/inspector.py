"""Agent details table — full run, all-steps view.

Mirrors the CSV export format: one row per agent per step, with leading
step/market columns so users can filter/sort exactly as they would in the CSV.

In live mode it shows the current step only (no completed steps available).
In historical mode it shows every step — step_idx is still accepted so the
component signature stays compatible with AnalysisPanel, but it is unused
in the all-steps path.
"""

from __future__ import annotations

import pandas as pd
import solara

from compute_permit_sim.schemas.columns import ColumnNames

# Columns kept for display — mirrors the CSV schema (agent_ prefix stripped)
_DISPLAY_COLS = [
    "step",
    "market_price",
    "market_supply",
    ColumnNames.ID,
    ColumnNames.IS_COMPLIANT,
    ColumnNames.HAS_PERMIT,
    ColumnNames.WAS_AUDITED,
    ColumnNames.WAS_CAUGHT,
    ColumnNames.CAUGHT_SOURCE,
    ColumnNames.COMPUTE_CAPACITY,
    ColumnNames.PLANNED_TRAINING_FLOPS,
    ColumnNames.USED_TRAINING_FLOPS,
    ColumnNames.REPORTED_TRAINING_FLOPS,
    ColumnNames.ECONOMIC_VALUE,
    ColumnNames.BID_PRICE,
    ColumnNames.PENALTY_AMOUNT,
    ColumnNames.PERMITS_WANTED,
    ColumnNames.AUDIT_COEFFICIENT,
    ColumnNames.CUMULATIVE_CAPABILITY,
]


def _build_all_steps_df(steps: list) -> pd.DataFrame:
    """Build a DataFrame identical in structure to the CSV exporter."""
    rows = []
    for step_res in steps:
        market_data = {
            "step": step_res.step,
            "market_price": step_res.market.price,
            "market_supply": step_res.market.supply,
        }
        for agent in step_res.agents:
            row = market_data.copy()
            row.update(agent.model_dump())
            rows.append(row)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@solara.component
def AgentDetailsTable(
    steps: list | None = None,
    step_idx: int = 0,
    live_agents_df: pd.DataFrame | None = None,
    is_live: bool = False,
) -> None:
    """Tabular, all-steps agent detail view.

    Historical mode: every step is included, sorted by step then agent id.
    Live mode: current live step only (no completed steps available yet).
    """
    agents_df: pd.DataFrame | None = None

    if is_live:
        # Live: show current snapshot only (no step/market cols available)
        agents_df = live_agents_df
    elif steps and len(steps) > 0:
        agents_df = _build_all_steps_df(steps)

    if agents_df is not None and not agents_df.empty:
        valid_cols = [c for c in _DISPLAY_COLS if c in agents_df.columns]
        with solara.Card("Agent Details"):
            solara.DataFrame(agents_df[valid_cols], items_per_page=20)
    else:
        with solara.Card("Agent Details"):
            solara.Markdown("*No agent data available.*")
