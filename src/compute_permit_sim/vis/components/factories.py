"""Component factories for chart groups.

3-column layout convention:
  All ``render_*`` methods use ``solara.Columns([1, 1, 1])`` with exactly 3
  child ``solara.Column()`` blocks. Empty columns act as spacers when fewer
  than 3 charts are needed to prevent Solara stretching 2 charts to 50% each.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
import solara

from compute_permit_sim.vis.components.charts import (
    AuditSourcePlot,
    AuditTargetingPlot,
    ComplianceDistributionPlot,
    RiskScatterPlot,
)


class ChartFactory:
    """Factory for building chart groups.

    Supports both step-level (``mode="step"``) and aggregate (``mode="aggregate"``)
    rendering of the full risk-analysis chart grid.
    """

    @staticmethod
    def render_risk_analysis(
        agents_df: pd.DataFrame | None,
        mode: Literal["aggregate", "step"] = "step",
        steps: list | None = None,
    ) -> None:
        """Two rows of risk analysis charts.

        Row 1: Risk scatter | Audit targeting | Compliance distribution
        Row 2: Caught by channel (4 detection sources) | (spacer) | (spacer)

        Args:
            agents_df: Step-level agent DataFrame (used in ``mode="step"``).
            mode: ``"step"`` or ``"aggregate"``. Determines data source and titles.
            steps: Full-run step list (used in ``mode="aggregate"``).
        """
        if mode == "step" and (agents_df is None or agents_df.empty):
            solara.Markdown("*No agent data available for risk analysis.*")
            return

        with solara.Columns([1, 1, 1]):
            with solara.Column():
                RiskScatterPlot(mode=mode, agents_df=agents_df, steps=steps)
            with solara.Column():
                AuditTargetingPlot(mode=mode, agents_df=agents_df, steps=steps)
            with solara.Column():
                ComplianceDistributionPlot(mode=mode, agents_df=agents_df, steps=steps)

        with solara.Columns([1, 1, 1]):
            with solara.Column():
                AuditSourcePlot(mode=mode, agents_df=agents_df, steps=steps)
            with solara.Column():
                pass  # reserved
            with solara.Column():
                pass  # reserved
