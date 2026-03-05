"""Scatter plot components — step-level risk analysis."""

from __future__ import annotations

import pandas as pd
import solara

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.vis.components.charts.base import validate_dataframe
from compute_permit_sim.vis.components.charts.expandable import ExpandableChart
from compute_permit_sim.vis.plotting import (
    plot_audit_source_distribution,
    plot_compliance_distribution,
    plot_scatter,
)
from compute_permit_sim.vis.transforms import classify_agent_outcome


@solara.component
def QuantitativeScatterPlot(agents_df: pd.DataFrame | None) -> None:
    """Scatter of Reported (X) vs True (Y) compute usage, colored by compliance.

    Points on the dashed y=x line are perfectly honest reporters.
    Points above it used more compute than reported (cheating).
    """
    if not validate_dataframe(
        agents_df,
        [ColumnNames.REPORTED_TRAINING_FLOPS, ColumnNames.USED_TRAINING_FLOPS],
    ):
        solara.Markdown("No data for scatter plot.")
        return

    assert agents_df is not None
    fig, ax = plot_scatter(
        agents_df,
        ColumnNames.REPORTED_TRAINING_FLOPS,
        ColumnNames.USED_TRAINING_FLOPS,
        "Risk Design: True vs Reported",
        "Reported FLOPs (r)",
        "True FLOPs (q)",
        color_logic="compliance",
    )

    max_val = (
        max(
            agents_df[ColumnNames.USED_TRAINING_FLOPS].max(),
            agents_df[ColumnNames.REPORTED_TRAINING_FLOPS].max(),
        )
        if not agents_df.empty
        else 1.0
    )
    ax.plot([0, max_val], [0, max_val], "k--", alpha=0.5, label="Honesty (y=x)")
    ax.legend()
    ExpandableChart(fig)


@solara.component
def ComplianceDistributionPlot(agents_df: pd.DataFrame | None) -> None:
    """Bar chart: Compliant / Uncaught / then per-source caught bars this step."""
    if not validate_dataframe(
        agents_df,
        [ColumnNames.IS_COMPLIANT, ColumnNames.WAS_CAUGHT],
    ):
        solara.Markdown("No compliance data.")
        return

    assert agents_df is not None
    df = classify_agent_outcome(agents_df)
    fig = plot_compliance_distribution(df)
    ExpandableChart(fig)


@solara.component
def AuditSourcePlot(agents_df: pd.DataFrame | None) -> None:
    """Bar chart: caught labs by detection channel (direct / backcheck / whistleblower / monitoring).

    Shows which enforcement mechanism is finding violators this step.
    Only caught labs are included; zero-count channels still appear as empty bars.
    """
    if not validate_dataframe(
        agents_df,
        [ColumnNames.WAS_CAUGHT],
    ):
        solara.Markdown("No audit data.")
        return

    assert agents_df is not None
    caught_df = classify_agent_outcome(agents_df)
    caught_only = caught_df[caught_df["outcome"] == "Caught"]
    fig = plot_audit_source_distribution(
        caught_only, title="Caught by Channel (This Step)"
    )
    ExpandableChart(fig)
