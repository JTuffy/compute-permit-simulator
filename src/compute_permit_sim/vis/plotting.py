"""Shared plotting utilities for consistent styling across UI and Exports.

All functions here accept pre-processed DataFrames (from vis.transforms) and
return ``matplotlib.figure.Figure`` objects. Zero Solara dependencies.

Design rules:
  - Every public function returns a ``Figure`` (or ``tuple[Figure, Axes]`` when
    the caller needs to annotate the axes further, e.g. adding reference lines).
  - All figures are created via ``create_figure()`` for uniform styling.
  - Color choices always go through ``CHART_COLOR_MAP`` or ``OUTCOME_COLORS``.
"""

from __future__ import annotations

import matplotlib
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.schemas.enums import AuditSource
from compute_permit_sim.vis.constants import CHART_COLOR_MAP, OUTCOME_COLORS

# Ensure non-interactive backend for thread safety in Solara/Exports
matplotlib.use("Agg")


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def create_figure(
    figsize: tuple[float, float] = (6, 4), dpi: int = 100
) -> tuple[Figure, Axes]:
    """Create a standardized matplotlib figure and axis.

    Returns:
        tuple (Figure, Axes)
    """
    fig = Figure(figsize=figsize, dpi=dpi)
    ax = fig.subplots()

    ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.2)
    ax.spines["bottom"].set_linewidth(1.2)

    return fig, ax


# ---------------------------------------------------------------------------
# Time-series plots
# ---------------------------------------------------------------------------


def plot_time_series(
    data: pd.Series | list,
    label: str,
    color_key: str,
    title: str | None = None,
    ylabel: str | None = None,
    ylim: tuple[float | None, float | None] | None = None,
) -> Figure:
    """Create a standard single-series time series plot.

    Args:
        data: Series or list of data points (one per step).
        label: Legend label.
        color_key: Key in ``CHART_COLOR_MAP`` or a raw hex string.
        title: Optional chart title.
        ylabel: Optional Y-axis label (defaults to *label*).
        ylim: Optional Y-axis limits.
    """
    fig, ax = create_figure(figsize=(6, 4))

    color = CHART_COLOR_MAP.get(color_key, color_key)
    ax.plot(data, label=label, color=color, linewidth=2.5, alpha=0.9)

    ax.set_xlabel("Step", fontsize=11, fontweight="500")
    ax.set_ylabel(ylabel or label, fontsize=11, fontweight="500")

    if title:
        ax.set_title(title, fontsize=12, fontweight="600")
    ax.legend(loc="best", framealpha=0.9, fontsize=10)
    if ylim:
        ax.set_ylim(bottom=ylim[0], top=ylim[1])

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Single-step snapshot plots
# ---------------------------------------------------------------------------


def plot_scatter(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    xlabel: str,
    ylabel: str,
    color_logic: str = "compliance",
) -> tuple[Figure, Axes]:
    """Create a standardized scatter plot with compliance coloring.

    Args:
        color_logic: ``'compliance'`` (green/red/black by status) or ``'simple'`` (blue).

    Returns:
        (Figure, Axes) — caller may add annotations before displaying.
    """
    fig, ax = create_figure(figsize=(6, 4))

    x = df[x_col]
    y = df[y_col]

    colors: list[str] = []
    if color_logic == "compliance":
        has_status = (
            ColumnNames.IS_COMPLIANT in df.columns
            and ColumnNames.WAS_CAUGHT in df.columns
        )
        if has_status:
            for _, row in df.iterrows():
                if row[ColumnNames.WAS_CAUGHT]:
                    colors.append(OUTCOME_COLORS["Caught"])
                elif not row[ColumnNames.IS_COMPLIANT]:
                    colors.append(OUTCOME_COLORS["Uncaught"])
                else:
                    colors.append(OUTCOME_COLORS["Compliant"])
        else:
            colors = [CHART_COLOR_MAP.get("blue", "#2196F3")] * len(df)
    else:
        colors = [CHART_COLOR_MAP.get("blue", "#2196F3")] * len(df)

    ax.scatter(x, y, c=colors, alpha=0.7, edgecolors="w", s=80)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    return fig, ax


def plot_compliance_distribution(
    df: pd.DataFrame,
    title: str = "Compliance Distribution",
) -> Figure:
    # Colours per detection channel (consistent across step and sim-wide views)
    SOURCE_COLORS: dict[str, str] = {
        AuditSource.DIRECT.value: "#B71C1C",  # dark red
        AuditSource.BACKCHECK.value: "#880E4F",  # dark pink
        AuditSource.WHISTLEBLOWER.value: "#4A148C",  # dark purple
        AuditSource.MONITORING.value: "#1A237E",  # dark blue
    }

    fig, ax = create_figure(figsize=(6, 4))

    if "outcome" not in df.columns:
        ax.text(0.5, 0.5, "No outcome data", transform=ax.transAxes, ha="center")
        fig.tight_layout()
        return fig

    outcome_counts = df["outcome"].value_counts()
    n_compliant = int(outcome_counts.get("Compliant", 0))
    n_uncaught = int(outcome_counts.get("Uncaught", 0))
    n_caught = int(outcome_counts.get("Caught", 0))

    # Build bar spec: always show Compliant + Uncaught, then per-source caught
    bar_labels: list[str] = []
    bar_values: list[int] = []
    bar_colors: list[str] = []

    bar_labels.append(f"Compliant\n(n={n_compliant})")
    bar_values.append(n_compliant)
    bar_colors.append(OUTCOME_COLORS["Compliant"])

    bar_labels.append(f"Uncaught\n(n={n_uncaught})")
    bar_values.append(n_uncaught)
    bar_colors.append(OUTCOME_COLORS["Uncaught"])

    if n_caught > 0 and "caught_source" in df.columns:
        caught_df = df[df["outcome"] == "Caught"]
        src_counts = (
            caught_df["caught_source"].dropna().astype(str).str.lower().value_counts()
        )
        for src in AuditSource:
            cnt = int(src_counts.get(src.value, 0))
            bar_labels.append(f"{src.value.capitalize()}\n(n={cnt})")
            bar_values.append(cnt)
            bar_colors.append(SOURCE_COLORS[src.value])
    elif n_caught > 0:
        # No source info but there are caught labs
        bar_labels.append(f"Caught\n(n={n_caught})")
        bar_values.append(n_caught)
        bar_colors.append(OUTCOME_COLORS["Caught"])

    bars = ax.bar(
        bar_labels,
        bar_values,
        color=bar_colors,
        alpha=0.88,
        edgecolor="black",
        linewidth=0.6,
    )
    for bar, count in zip(bars, bar_values):
        if count > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.2,
                str(count),
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
            )

    ax.set_ylabel("Number of Labs")
    ax.set_title(title)
    ax.set_ylim(0, max(bar_values) * 1.3 if max(bar_values) > 0 else 5)
    ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    return fig


def plot_audit_coefficient_distribution(
    df: pd.DataFrame,
    title: str = "Audit Coefficient Distribution",
) -> Figure:
    """Histogram of per-lab audit coefficient values in the selected step.

    A spread of values shows that escalated enforcement has targeted specific
    firms. A uniform spike at 1.0 means no escalation has occurred.

    Args:
        df: Agent DataFrame with ``audit_coefficient`` column.
    """
    fig, ax = create_figure(figsize=(5, 4))

    if ColumnNames.AUDIT_COEFFICIENT not in df.columns:
        ax.text(
            0.5, 0.5, "No audit_coefficient data", transform=ax.transAxes, ha="center"
        )
        fig.tight_layout()
        return fig

    values = df[ColumnNames.AUDIT_COEFFICIENT].dropna()
    ax.hist(
        values,
        bins=min(20, max(5, len(values) // 2)),
        color=CHART_COLOR_MAP.get("blue", "#2196F3"),
        alpha=0.8,
        edgecolor="black",
    )
    ax.axvline(
        x=1.0, color="gray", linestyle="--", linewidth=1.5, label="Baseline (1.0)"
    )
    ax.set_xlabel("Audit Coefficient c(i)")
    ax.set_ylabel("Number of Labs")
    ax.set_title(title)
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Shared audit targeting (step-wise and sim-wide)
# ---------------------------------------------------------------------------


def plot_audit_targeting(
    compliant_rate: float,
    noncompliant_rate: float,
    n_compliant: int,
    n_noncompliant: int,
    title: str = "Audit Targeting",
) -> Figure:
    """Bar chart: audit rate for compliant vs non-compliant labs.

    Used by both the step-wise (AuditSourceBreakdownStepPlot) and sim-wide
    (SimAuditTargetingPlot) components — same visual, different data sources.

    Green = compliant labs audited (ideally low — don't waste capacity).
    Red   = non-compliant labs audited (ideally high — targeted enforcement).

    Args:
        compliant_rate: Fraction of compliant labs audited (0–1).
        noncompliant_rate: Fraction of non-compliant labs audited (0–1).
        n_compliant: Total compliant lab-steps observed.
        n_noncompliant: Total non-compliant lab-steps observed.
        title: Chart title.
    """
    fig, ax = create_figure(figsize=(6, 4))

    cr = compliant_rate * 100
    nr = noncompliant_rate * 100
    categories = [
        f"Compliant\n(n={n_compliant})",
        f"Non-Compliant\n(n={n_noncompliant})",
    ]
    rates = [cr, nr]
    # Green for compliant (good to audit low), red for non-compliant (good to audit high)
    colors = [OUTCOME_COLORS["Compliant"], OUTCOME_COLORS["Uncaught"]]

    bars = ax.bar(
        categories, rates, color=colors, alpha=0.88, edgecolor="black", linewidth=0.6
    )
    for bar, rate in zip(bars, rates):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{rate:.1f}%",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
        )

    ax.set_ylabel("Audit Rate (%)")
    ax.set_title(title, fontsize=12, fontweight="600")
    ax.set_ylim(0, max(rates) * 1.3 if max(rates) > 0 else 10)
    ax.yaxis.grid(True, alpha=0.25)  # y-only grid overrides create_figure default
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Audit source distribution (step-wise and sim-wide)
# ---------------------------------------------------------------------------


# Consistent bar colours per AuditSource channel
AUDIT_SOURCE_COLORS: dict[str, str] = {
    AuditSource.DIRECT.value: "#B71C1C",  # dark red
    AuditSource.BACKCHECK.value: "#880E4F",  # dark pink
    AuditSource.WHISTLEBLOWER.value: "#4A148C",  # dark purple
    AuditSource.MONITORING.value: "#1A237E",  # dark blue
}


def plot_audit_source_distribution(
    df: pd.DataFrame,
    title: str = "Caught by Audit Channel",
) -> Figure:
    """Bar chart: number of caught labs per AuditSource detection channel.

    Shows how enforcement is actually finding violators — direct inspection,
    back-checks, whistleblower reports, or ongoing monitoring — rather than
    just aggregating all catches into one bucket.

    Args:
        df: DataFrame with ``caught_source`` column (lowercase AuditSource values).
            Only rows with a non-null caught_source are included.
            Pass the full agents_df for a single step, or the output of
            ``aggregate_compliance_distribution`` for the sim-wide view.
    """
    fig, ax = create_figure(figsize=(6, 4))

    if "caught_source" not in df.columns:
        ax.text(0.5, 0.5, "No audit source data", transform=ax.transAxes, ha="center")
        fig.tight_layout()
        return fig

    src_counts = df["caught_source"].dropna().astype(str).str.lower().value_counts()

    labels = []
    values = []
    colors = []
    for src in AuditSource:
        cnt = int(src_counts.get(src.value, 0))
        labels.append(f"{src.value.capitalize()}\n(n={cnt})")
        values.append(cnt)
        colors.append(AUDIT_SOURCE_COLORS[src.value])

    bars = ax.bar(
        labels, values, color=colors, alpha=0.88, edgecolor="black", linewidth=0.6
    )
    for bar, count in zip(bars, values):
        if count > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.15,
                str(count),
                ha="center",
                va="bottom",
                fontsize=11,
                fontweight="bold",
            )

    ax.set_ylabel("Labs Caught")
    ax.set_title(title, fontsize=12, fontweight="600")
    ax.set_ylim(0, max(values) * 1.3 if max(values) > 0 else 5)
    ax.yaxis.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig
