"""Scatter plot components for risk, gain, and capacity analysis."""

import pandas as pd
import solara
from matplotlib.figure import Figure

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.vis.components.charts.base import validate_dataframe
from compute_permit_sim.vis.constants import CHART_COLOR_MAP
from compute_permit_sim.vis.plotting import plot_scatter


@solara.component
def QuantitativeScatterPlot(agents_df: pd.DataFrame | None):
    """Scatter plot of Reported (X) vs True (Y) compute for risk analysis.

    Shows the gap between reported and actual compute usage, colored by compliance.
    """
    if not validate_dataframe(
        agents_df,
        [ColumnNames.REPORTED_COMPUTE, ColumnNames.USED_COMPUTE],
        "No data for scatter plot.",
    ):
        solara.Markdown("No data for scatter plot.")
        return

    fig, ax = plot_scatter(
        agents_df,
        ColumnNames.REPORTED_COMPUTE,
        ColumnNames.USED_COMPUTE,
        "Risk Design: True vs Reported",
        "Reported Compute (r)",
        "True Compute (q)",
        color_logic="compliance",
    )

    max_val = (
        max(
            agents_df[ColumnNames.USED_COMPUTE].max(),
            agents_df[ColumnNames.REPORTED_COMPUTE].max(),
        )
        if not agents_df.empty
        else 1.0
    )
    ax.plot([0, max_val], [0, max_val], "k--", alpha=0.5, label="Honesty (y=x)")
    ax.legend()

    solara.FigureMatplotlib(fig)


@solara.component
def CheatingGainPlot(agents_df: pd.DataFrame | None):
    """Scatter plot of Economic Value vs Step Profit.

    Shows whether higher-value firms benefit more from cheating.
    """
    if not validate_dataframe(
        agents_df,
        [
            ColumnNames.ECONOMIC_VALUE,
            ColumnNames.STEP_PROFIT,
            ColumnNames.IS_COMPLIANT,
        ],
        "Missing data for gain plot.",
    ):
        solara.Markdown("Missing data for gain plot.")
        return

    fig = Figure(figsize=(6, 5), dpi=100)
    ax = fig.subplots()

    x = agents_df[ColumnNames.ECONOMIC_VALUE]
    y = agents_df[ColumnNames.STEP_PROFIT]
    colors = agents_df[ColumnNames.IS_COMPLIANT].map(
        {True: CHART_COLOR_MAP["green"], False: CHART_COLOR_MAP["red"]}
    )

    ax.scatter(x, y, c=colors, alpha=0.7, edgecolors="w", s=80)

    ax.set_xlabel("Economic Value (Potential)")
    ax.set_ylabel("Step Profit (Realized)")
    ax.set_title("Cheating Gain Analysis")
    ax.grid(True, alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    solara.FigureMatplotlib(fig)


@solara.component
def CapacityUtilizationPlot(agents_df: pd.DataFrame | None):
    """Scatter plot of Capacity vs Reported Compute.

    Shows the relationship between firm size and reported utilization.
    """
    if not validate_dataframe(
        agents_df,
        [
            ColumnNames.CAPACITY,
            ColumnNames.REPORTED_COMPUTE,
            ColumnNames.IS_COMPLIANT,
        ],
        "Missing data for capacity plot.",
    ):
        solara.Markdown("Missing data for capacity plot.")
        return

    fig = Figure(figsize=(6, 5), dpi=100)
    ax = fig.subplots()

    x = agents_df[ColumnNames.CAPACITY]
    y = agents_df[ColumnNames.REPORTED_COMPUTE]
    colors = agents_df[ColumnNames.IS_COMPLIANT].map(
        {True: CHART_COLOR_MAP["green"], False: CHART_COLOR_MAP["red"]}
    )

    ax.scatter(x, y, c=colors, alpha=0.7, edgecolors="w", s=80)

    max_val = max(x.max(), y.max()) if not x.empty else 1
    ax.plot([0, max_val], [0, max_val], "k--", alpha=0.3, label="100% Util Reported")

    ax.set_xlabel("Max Capacity (q_max)")
    ax.set_ylabel("Reported Compute (r)")
    ax.set_title("Reported Utilization vs Scale")
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    solara.FigureMatplotlib(fig)
