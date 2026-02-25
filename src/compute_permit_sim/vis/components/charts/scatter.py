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
        [ColumnNames.REPORTED_TRAINING_FLOPS, ColumnNames.USED_TRAINING_FLOPS],
        "No data for scatter plot.",
    ):
        solara.Markdown("No data for scatter plot.")
        return

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

    solara.FigureMatplotlib(fig)



@solara.component
def CapacityUtilizationPlot(agents_df: pd.DataFrame | None):
    """Scatter plot of Capacity vs Reported Compute.

    Shows the relationship between firm size and reported utilization.
    """
    if not validate_dataframe(
        agents_df,
        [
            ColumnNames.PLANNED_TRAINING_FLOPS,
            ColumnNames.REPORTED_TRAINING_FLOPS,
            ColumnNames.IS_COMPLIANT,
        ],
        "Missing data for capacity plot.",
    ):
        solara.Markdown("Missing data for capacity plot.")
        return

    fig = Figure(figsize=(6, 5), dpi=100)
    ax = fig.subplots()

    x = agents_df[ColumnNames.PLANNED_TRAINING_FLOPS]
    y = agents_df[ColumnNames.REPORTED_TRAINING_FLOPS]
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
