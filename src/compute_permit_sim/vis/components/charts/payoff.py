"""Payoff comparison plots."""

import pandas as pd
import solara
from matplotlib.figure import Figure

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.vis.components.charts.base import validate_dataframe


@solara.component
def PayoffByStrategyPlot(agents_df: pd.DataFrame | None):
    """Bar chart comparing average economic value by strategy outcome.

    Shows economic value at stake for: compliant, caught cheating, and uncaught cheating.
    """
    if not validate_dataframe(
        agents_df,
        [
            ColumnNames.IS_COMPLIANT,
            ColumnNames.WAS_CAUGHT,
            ColumnNames.ECONOMIC_VALUE,
        ],
        "Missing required columns for payoff plot.",
    ):
        solara.Markdown("No data for payoff plot.")
        return

    assert agents_df is not None

    compliant = agents_df[agents_df[ColumnNames.IS_COMPLIANT]]
    cheated_caught = agents_df[
        ~agents_df[ColumnNames.IS_COMPLIANT] & agents_df[ColumnNames.WAS_CAUGHT]
    ]
    cheated_uncaught = agents_df[
        ~agents_df[ColumnNames.IS_COMPLIANT] & ~agents_df[ColumnNames.WAS_CAUGHT]
    ]

    avg_compliant = (
        compliant[ColumnNames.ECONOMIC_VALUE].mean() if len(compliant) > 0 else 0
    )
    avg_caught = (
        cheated_caught[ColumnNames.ECONOMIC_VALUE].mean()
        if len(cheated_caught) > 0
        else 0
    )
    avg_uncaught = (
        cheated_uncaught[ColumnNames.ECONOMIC_VALUE].mean()
        if len(cheated_uncaught) > 0
        else 0
    )

    fig = Figure(figsize=(5, 4))
    ax = fig.subplots()

    categories = ["Compliant", "Caught", "Uncaught"]
    payoffs = [avg_compliant, avg_caught, avg_uncaught]
    colors = ["#4CAF50", "#000000", "#F44336"]
    counts = [len(compliant), len(cheated_caught), len(cheated_uncaught)]

    bars = ax.bar(categories, payoffs, color=colors, alpha=0.8, edgecolor="black")

    for bar, payoff, count in zip(bars, payoffs, counts):
        y_pos = bar.get_height()
        label_y = (
            y_pos + 0.02 * abs(max(payoffs) - min(payoffs))
            if y_pos >= 0
            else y_pos - 0.05 * abs(max(payoffs) - min(payoffs))
        )
        va = "bottom" if y_pos >= 0 else "top"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            label_y,
            f"${payoff:.2f}\n(n={count})",
            ha="center",
            va=va,
            fontsize=9,
            fontweight="bold",
        )

    ax.set_ylabel("Avg Economic Value (M$)")
    ax.set_title("Economic Value by Strategy")
    ax.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="y")
    y_min = min(0, min(payoffs) * 1.3)
    y_max = max(payoffs) * 1.3 if max(payoffs) > 0 else 1
    ax.set_ylim(y_min, y_max)
    fig.tight_layout()
    solara.FigureMatplotlib(fig)
