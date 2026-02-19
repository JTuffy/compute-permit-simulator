"""Shared plotting utilities for consistent styling across UI and Exports."""

import matplotlib
import pandas as pd
from matplotlib.figure import Figure

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.vis.constants import CHART_COLOR_MAP

# Ensure non-interactive backend for thread safety in Solara/Exports
matplotlib.use("Agg")


def create_figure(figsize=(6, 4), dpi=100) -> tuple[Figure, any]:
    """Create a standardized matplotlib figure and axis.

    Returns:
        tuple (Figure, Axes)
    """
    fig = Figure(figsize=figsize, dpi=dpi)
    ax = fig.subplots()

    # Common Styling
    ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.2)
    ax.spines["bottom"].set_linewidth(1.2)

    return fig, ax


def plot_time_series(
    data: pd.Series | list,
    label: str,
    color_key: str,
    title: str | None = None,
    ylabel: str | None = None,
    ylim: tuple[float, float] | None = None,
) -> Figure:
    """Create a standard time series plot.

    Args:
        data: Series or list of data points
        label: Legend label
        color_key: Key in CHART_COLOR_MAP (e.g., 'blue', 'green') or hex
        title: Optional chart title
        ylabel: Optional Y-axis label (defaults to label)
        ylim: Optional Y-axis limits
    """
    fig, ax = create_figure(figsize=(8, 4))

    # Type-safe color lookup: use CHART_COLOR_MAP if available, fall back to color_key as hex
    color = (
        CHART_COLOR_MAP.get(color_key) if isinstance(CHART_COLOR_MAP, dict) else None
    )
    if color is None:
        color = color_key  # Fall back to raw color_key (e.g., hex string)

    ax.plot(data, label=label, color=color, linewidth=2.5, alpha=0.9)

    ax.set_xlabel("Step", fontsize=11, fontweight="500")
    ax.set_ylabel(ylabel or label, fontsize=11, fontweight="500")

    if title:
        ax.set_title(title, fontsize=12, fontweight="600")

    ax.legend(loc="best", framealpha=0.9, fontsize=10)

    if ylim:
        ax.set_ylim(ylim)

    fig.tight_layout()
    return fig


def plot_scatter(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    xlabel: str,
    ylabel: str,
    color_logic: str = "compliance",
) -> Figure:
    """Create a standardized scatter plot with compliance coloring.

    Args:
        color_logic: 'compliance' (green/red/black) or 'simple' (blue)
    """
    fig, ax = create_figure(figsize=(6, 5))

    x = df[x_col]
    y = df[y_col]

    colors = []
    if color_logic == "compliance":
        has_status = (
            ColumnNames.IS_COMPLIANT in df.columns
            and ColumnNames.WAS_CAUGHT in df.columns
        )
        if has_status:
            for _, row in df.iterrows():
                if row[ColumnNames.WAS_CAUGHT]:
                    colors.append("black")
                elif not row[ColumnNames.IS_COMPLIANT]:
                    colors.append("red")  # CHART_COLOR_MAP["red"]
                else:
                    colors.append("green")  # CHART_COLOR_MAP["green"]
        else:
            colors = ["blue"] * len(df)
    else:
        colors = ["blue"] * len(df)

    ax.scatter(x, y, c=colors, alpha=0.7, edgecolors="w", s=80)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    #
    return fig, ax


def plot_deterrence_frontier(
    df: pd.DataFrame,
    title: str = "Deterrence Frontier",
) -> tuple[Figure, any]:
    """Scatter plot of Economic Value vs Risk Profile, colored by outcome."""
    fig, ax = create_figure(figsize=(7, 5))

    # X: Economic Value (Incentive), Y: Risk Profile (Sensitivity)
    # Check if columns exist (snake_case from pydantic dump)
    x_col = ColumnNames.ECONOMIC_VALUE
    y_col = ColumnNames.RISK_PROFILE

    if x_col not in df.columns or y_col not in df.columns:
        return fig, ax  # empty

    colors = []
    labels = []

    # Logic:
    # Green: Compliant
    # Red: Non-Compliant (Cheated) but NOT Caught
    # Black: Caught (Non-Compliant + Caught)

    has_status = (
        ColumnNames.IS_COMPLIANT in df.columns and ColumnNames.WAS_CAUGHT in df.columns
    )

    if has_status:
        for _, row in df.iterrows():
            if row[ColumnNames.WAS_CAUGHT]:
                colors.append("black")
                labels.append("Caught")
            elif not row[ColumnNames.IS_COMPLIANT]:
                colors.append("red")
                labels.append("Cheated")
            else:
                colors.append("green")
                labels.append("Compliant")
    else:
        colors = ["blue"] * len(df)

    ax.scatter(df[x_col], df[y_col], c=colors, alpha=0.7, edgecolors="w", s=80)

    ax.set_xlabel("Economic Value (Incentive)")
    ax.set_ylabel("Risk Profile (Sensitivity)")
    ax.set_title(title)

    # Custom Legend
    from matplotlib.lines import Line2D

    custom_lines = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="green",
            markersize=10,
            label="Compliant",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="red",
            markersize=10,
            label="Cheated",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="black",
            markersize=10,
            label="Caught",
        ),
    ]
    ax.legend(handles=custom_lines, loc="best")

    return fig, ax


def plot_payoff_distribution(
    df: pd.DataFrame,
    title: str = "Payoff by Strategy",
) -> tuple[Figure, any]:
    """Bar chart of Average Step Profit for Compliant vs Non-Compliant/Caught."""
    fig, ax = create_figure(figsize=(6, 5))

    if ColumnNames.STEP_PROFIT not in df.columns:
        return fig, ax

    # Strategies: Compliant, Cheated (Uncaught), Caught
    # We group by status and take mean profit

    groups = {"Compliant": [], "Uncaught": [], "Caught": []}

    if ColumnNames.IS_COMPLIANT in df.columns and ColumnNames.WAS_CAUGHT in df.columns:
        for _, row in df.iterrows():
            profit = row[ColumnNames.STEP_PROFIT]
            if row[ColumnNames.WAS_CAUGHT]:
                groups["Caught"].append(profit)
            elif not row[ColumnNames.IS_COMPLIANT]:
                groups["Uncaught"].append(profit)
            else:
                groups["Compliant"].append(profit)

    # Calculate means
    means = []
    labels = []
    colors = []

    # Order: Compliant, Caught, Uncaught
    if groups["Compliant"]:
        means.append(sum(groups["Compliant"]) / len(groups["Compliant"]))
        labels.append(f"Compliant\n(n={len(groups['Compliant'])})")
        colors.append("green")

    if groups["Caught"]:
        means.append(sum(groups["Caught"]) / len(groups["Caught"]))
        labels.append(f"Caught\n(n={len(groups['Caught'])})")
        colors.append("black")

    if groups["Uncaught"]:
        means.append(sum(groups["Uncaught"]) / len(groups["Uncaught"]))
        labels.append(f"Uncaught\n(n={len(groups['Uncaught'])})")
        colors.append("red")

    if not means:
        return fig, ax

    bars = ax.bar(labels, means, color=colors, alpha=0.7, edgecolor="black")

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"${height:.2f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),  # 3 points vertical offset
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    ax.set_ylabel("Avg Net Value (M$)")
    ax.set_title(title)
    # Increase y-limit slightly for labels
    if means:
        ax.set_ylim(top=max(means) * 1.15)

    return fig, ax
