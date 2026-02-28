"""Component factories and builders to reduce duplication and improve composition."""

import pandas as pd
import solara

from compute_permit_sim.vis.components.cards import MetricCard
from compute_permit_sim.vis.components.charts import (
    AuditTargetingPlot,
    CapacityUtilizationPlot,
    LabDecisionPlot,
    PayoffByStrategyPlot,
    QuantitativeScatterPlot,
)


class ChartFactory:
    """Factory for building collections of charts based on available data.

    Reduces boilerplate in panels/analysis.py by providing structured ways
    to render sets of related charts.
    """

    @staticmethod
    def render_risk_analysis(agents_df: pd.DataFrame | None):
        """Render risk-related charts: scatter, audit targeting, capacity."""
        if agents_df is None or agents_df.empty:
            solara.Markdown("No agent data available for risk analysis.")
            return

        with solara.Columns([1, 1, 1]):
            with solara.Column():
                QuantitativeScatterPlot(agents_df)
            with solara.Column():
                AuditTargetingPlot(agents_df)
            with solara.Column():
                CapacityUtilizationPlot(agents_df)

    @staticmethod
    def render_deterrence_analysis(
        agents_df: pd.DataFrame | None, audit_prob: float, penalty: float
    ):
        """Render deterrence-related charts: lab decision, payoff by strategy, cheating gain."""
        if agents_df is None or agents_df.empty:
            solara.Markdown("No agent data available for deterrence analysis.")
            return

        with solara.Columns([1, 1, 1]):
            with solara.Column():
                LabDecisionPlot(agents_df, audit_prob, penalty)
            with solara.Column():
                PayoffByStrategyPlot(agents_df)


class MetricCardFactory:
    """Factory for building metric displays.

    Standardizes metric card styling and formatting across the UI.
    """

    @staticmethod
    def create_compliance_card(compliance_value: float) -> None:
        """Create a compliance metric card."""
        color = "success" if compliance_value >= 0.8 else "warning"
        display_val = f"{compliance_value:.1%}"
        MetricCard("Compliance", display_val, color_variant=color)

    @staticmethod
    def create_price_card(price_value: float) -> None:
        """Create a price metric card."""
        display_val = f"${price_value:.2f}"
        MetricCard("Market Price", display_val, color_variant="primary")

    @staticmethod
    def create_custom_metric(label: str, value: str, variant: str = "primary") -> None:
        """Create a custom metric card."""
        MetricCard(label, value, color_variant=variant)
