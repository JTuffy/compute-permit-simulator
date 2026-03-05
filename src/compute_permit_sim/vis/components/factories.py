"""Component factories for step-level chart groups.

3-column layout convention:
  All ``render_*`` methods use ``solara.Columns([1, 1, 1])`` with exactly 3
  child ``solara.Column()`` blocks. Empty columns act as spacers when fewer
  than 3 charts are needed to prevent Solara stretching 2 charts to 50% each.
"""

from __future__ import annotations

import pandas as pd
import solara

from compute_permit_sim.vis.components.cards import MetricCard
from compute_permit_sim.vis.components.charts import (
    AuditSourceBreakdownStepPlot,
    AuditSourcePlot,
    ComplianceDistributionPlot,
    QuantitativeScatterPlot,
)


class ChartFactory:
    """Factory for building step-level chart groups.

    One group is currently supported:
      - **risk_analysis**: scatter (true vs reported FLOPs), audit targeting,
        compliance distribution, and audit source breakdown (4 channels).
    """

    @staticmethod
    def render_risk_analysis(agents_df: pd.DataFrame | None) -> None:
        """Two rows of step-level charts.

        Row 1: Risk scatter | Audit targeting | Compliance distribution
        Row 2: Caught by channel (4 detection sources) | (spacer) | (spacer)
        """
        if agents_df is None or agents_df.empty:
            solara.Markdown("No agent data available for risk analysis.")
            return

        # Row 1: core risk analysis
        with solara.Columns([1, 1, 1]):
            with solara.Column():
                QuantitativeScatterPlot(agents_df)
            with solara.Column():
                AuditSourceBreakdownStepPlot(agents_df)
            with solara.Column():
                ComplianceDistributionPlot(agents_df)

        # Row 2: audit source breakdown (4 detection channels)
        with solara.Columns([1, 1, 1]):
            with solara.Column():
                AuditSourcePlot(agents_df)
            with solara.Column():
                pass  # reserved
            with solara.Column():
                pass  # reserved


class MetricCardFactory:
    """Factory for building metric display chips."""

    @staticmethod
    def create_compliance_card(compliance_value: float) -> None:
        """Create a compliance metric card."""
        color = "success" if compliance_value >= 0.8 else "warning"
        MetricCard("Compliance", f"{compliance_value:.1%}", color_variant=color)

    @staticmethod
    def create_price_card(price_value: float) -> None:
        """Create a price metric card."""
        MetricCard("Market Price", f"${price_value:.2f}", color_variant="primary")

    @staticmethod
    def create_custom_metric(label: str, value: str, variant: str = "primary") -> None:
        """Create a custom metric card."""
        MetricCard(label, value, color_variant=variant)
