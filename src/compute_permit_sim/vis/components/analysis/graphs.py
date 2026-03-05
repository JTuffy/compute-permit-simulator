"""Sim-level run summary — shown above the step slider.

Row 1 (always visible — live + historical):
  Compliance Rate | Permit Price | (spacer)

Row 2 (historical only — mirrors the 3 step-wise charts):
  Risk Scatter (all steps) | Audit Targeting (full run) | Compliance Distribution (full run)

Row 3 (historical only):
  Caught by Channel (full run) | (spacer) | (spacer)
"""

from __future__ import annotations

import pandas as pd
import solara

from compute_permit_sim.vis.components.charts.expandable import ExpandableChart
from compute_permit_sim.vis.components.charts.longitudinal import (
    SimAuditSourcePlot,
    SimAuditTargetingPlot,
    SimComplianceDistributionPlot,
    SimRiskScatterPlot,
)
from compute_permit_sim.vis.plotting import plot_time_series


@solara.component
def RunGraphs(
    compliance_series: list | pd.Series,
    caught_series: list | pd.Series,
    price_series: list | pd.Series,
    steps: list | None = None,
    is_playing: bool = False,
) -> None:
    """Sim-level run summary panels."""
    with solara.Card("Run Summary"):
        # --- In-panel progress banner (live only) ---
        if is_playing:
            with solara.Row(
                style="align-items: center; gap: 12px; margin-bottom: 8px;"
            ):
                solara.v.ProgressCircular(
                    indeterminate=True, color="primary", size=20, width=3
                )
                solara.Text("Simulating…", style="color: #888; font-style: italic;")

        # --- Row 1: Core time series (live + historical) ---
        with solara.Columns([1, 1, 1]):
            with solara.Column():
                if compliance_series:
                    fig = plot_time_series(
                        compliance_series,
                        "Compliance Rate",
                        "green",
                        title="Compliance Rate",
                        ylabel="Rate (0–1)",
                        ylim=(-0.05, 1.05),
                    )
                    ExpandableChart(fig)
                else:
                    solara.Markdown("*No compliance data yet*")

            with solara.Column():
                if price_series:
                    fig = plot_time_series(
                        price_series,
                        "Market Price",
                        "blue",
                        title="Permit Price",
                        ylabel="Price ($)",
                    )
                    ExpandableChart(fig)
                else:
                    solara.Markdown("*No price data yet*")

            with solara.Column():
                pass  # reserved

        # --- Row 2: Sim-wide aggregates (historical only) ---
        # Mirrors the 3 step-wise charts but consolidated over all steps
        if steps:
            with solara.Columns([1, 1, 1]):
                with solara.Column():
                    SimRiskScatterPlot(steps)
                with solara.Column():
                    SimAuditTargetingPlot(steps)
                with solara.Column():
                    SimComplianceDistributionPlot(steps)

            # --- Row 3: Full-run audit source breakdown (4 detection channels) ---
            with solara.Columns([1, 1, 1]):
                with solara.Column():
                    SimAuditSourcePlot(steps)
                with solara.Column():
                    pass  # reserved
                with solara.Column():
                    pass  # reserved
