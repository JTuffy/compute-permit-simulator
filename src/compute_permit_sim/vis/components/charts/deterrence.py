"""Audit targeting chart — step and aggregate modes.

Shows what fraction of compliant vs non-compliant labs are audited.
In step mode: enforcement targeting for the currently selected step.
In aggregate mode: targeting efficiency across the full run.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
import solara

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.vis.components.charts.base import validate_dataframe
from compute_permit_sim.vis.components.charts.expandable import ExpandableChart
from compute_permit_sim.vis.plotting import plot_audit_targeting
from compute_permit_sim.vis.transforms import aggregate_audit_targeting


@solara.component
def AuditTargetingPlot(
    mode: Literal["aggregate", "step"],
    agents_df: pd.DataFrame | None = None,
    steps: list | None = None,
) -> None:
    """Bar chart: audit rate for Compliant vs Non-Compliant labs.

    In step mode: derived from ``agents_df`` for the current step.
    In aggregate mode: aggregated across all steps from ``steps``.

    Green = compliant labs audited (low rate is good — not wasting capacity).
    Red = non-compliant labs audited (high rate is good — targeted enforcement).
    """
    if mode == "step":
        if not validate_dataframe(
            agents_df,
            [ColumnNames.IS_COMPLIANT, ColumnNames.WAS_AUDITED],
        ):
            solara.Markdown("*No data for audit targeting plot.*")
            return

        assert agents_df is not None
        compliant = agents_df[agents_df[ColumnNames.IS_COMPLIANT]]
        noncompliant = agents_df[~agents_df[ColumnNames.IS_COMPLIANT]]

        compliant_rate = (
            float(compliant[ColumnNames.WAS_AUDITED].mean())
            if len(compliant) > 0
            else 0.0
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

    else:
        # Aggregate mode — pool all steps
        if not steps:
            solara.Markdown("*No step data.*")
            return
        stats = aggregate_audit_targeting(steps)
        fig = plot_audit_targeting(
            compliant_rate=stats["compliant_rate"],
            noncompliant_rate=stats["noncompliant_rate"],
            n_compliant=stats["compliant_total"],
            n_noncompliant=stats["noncompliant_total"],
            title="Audit Targeting (Full Run)",
        )
        ExpandableChart(fig)
