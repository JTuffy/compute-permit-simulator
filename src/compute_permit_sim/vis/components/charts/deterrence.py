"""Audit targeting chart — step-level view.

Shows what fraction of compliant vs non-compliant labs were audited
in the current step, so you can see if enforcement is targeting the
right firms on a step-by-step basis.
"""

from __future__ import annotations

import pandas as pd
import solara

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.vis.components.charts.base import validate_dataframe
from compute_permit_sim.vis.components.charts.expandable import ExpandableChart
from compute_permit_sim.vis.plotting import plot_audit_targeting


@solara.component
def AuditSourceBreakdownStepPlot(agents_df: pd.DataFrame | None) -> None:
    """Bar chart: audit rate for Compliant vs Non-Compliant labs this step.

    Green = compliant labs audited (low rate is good — not wasting capacity).
    Red = non-compliant labs audited (high rate is good — targeted enforcement).
    """
    if not validate_dataframe(
        agents_df,
        [ColumnNames.IS_COMPLIANT, ColumnNames.WAS_AUDITED],
    ):
        solara.Markdown("No data for audit targeting plot.")
        return

    assert agents_df is not None
    compliant = agents_df[agents_df[ColumnNames.IS_COMPLIANT]]
    noncompliant = agents_df[~agents_df[ColumnNames.IS_COMPLIANT]]

    compliant_rate = (
        float(compliant[ColumnNames.WAS_AUDITED].mean()) if len(compliant) > 0 else 0.0
    )
    noncompliant_rate = (
        float(noncompliant[ColumnNames.WAS_AUDITED].mean())
        if len(noncompliant) > 0
        else 0.0
    )

    fig = plot_audit_targeting(
        compliant_rate=compliant_rate,
        noncompliant_rate=noncompliant_rate,
        n_compliant=len(compliant),
        n_noncompliant=len(noncompliant),
        title="Audit Targeting (This Step)",
    )
    ExpandableChart(fig)
