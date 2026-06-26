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

import textwrap
from typing import NamedTuple, cast

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.schemas.enums import AuditSource
from compute_permit_sim.vis.constants import CHART_COLOR_MAP, OUTCOME_COLORS

# Ensure non-interactive backend for thread safety in Solara/Exports
matplotlib.use("Agg")


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _wrap(text: str, width: int = 48) -> str:
    """Wrap *text* to at most *width* characters per line.

    Applied to all dynamic strings (scenario names, parameter labels) used
    in chart titles and axis labels so they never overflow figure bounds.
    """
    return textwrap.fill(text, width=width)


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
    ax.set_ylabel(_wrap(ylabel or label), fontsize=11, fontweight="500")

    if title:
        ax.set_title(_wrap(title), fontsize=12, fontweight="600")
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
    ax.set_xlabel(_wrap(xlabel))
    ax.set_ylabel(_wrap(ylabel))
    ax.set_title(_wrap(title))
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
    ax.set_title(_wrap(title))
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
    ax.set_title(_wrap(title))
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
    ax.set_title(_wrap(title), fontsize=12, fontweight="600")
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
    ax.set_title(_wrap(title), fontsize=12, fontweight="600")
    ax.set_ylim(0, max(values) * 1.3 if max(values) > 0 else 5)
    ax.yaxis.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Batch / Monte Carlo plots
# ---------------------------------------------------------------------------


def plot_mc_trajectory(result) -> "Figure":
    """Plot compliance trajectory: mean ± 1 SD band over simulation steps.

    Args:
        result: A ``MonteCarloResult`` with ``step_compliance`` populated.

    Returns:
        Matplotlib Figure.
    """
    from compute_permit_sim.schemas.batch import MonteCarloResult

    if not isinstance(result, MonteCarloResult):
        raise TypeError(f"Expected MonteCarloResult, got {type(result)}")

    fig, ax = create_figure(figsize=(7, 4))
    steps = list(range(1, len(result.step_compliance) + 1))
    means = [s.mean for s in result.step_compliance]
    lows = [max(0.0, s.mean - s.std) for s in result.step_compliance]
    highs = [min(1.0, s.mean + s.std) for s in result.step_compliance]

    color = CHART_COLOR_MAP.get("compliant", "#42A5F5")
    ax.plot(steps, means, color=color, linewidth=2, label="Mean compliance")
    ax.fill_between(steps, lows, highs, alpha=0.18, color=color, label="± 1 SD")
    ax.axhline(
        1.0,
        color="#66BB6A",
        linewidth=1,
        linestyle="--",
        alpha=0.5,
        label="100% threshold",
    )

    ax.set_xlim(1, max(steps))
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Simulation Step")
    ax.set_ylabel("Compliance Rate")
    ax.set_title(
        _wrap(
            f"Compliance Trajectory — {result.scenario_name} ({result.n_runs} seeds)"
        ),
        fontsize=11,
        fontweight="600",
    )
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1))
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


def plot_mc_violator_trajectory(result) -> "Figure":
    """Plot violator-count trajectory: mean ± 1 SD band over simulation steps.

    Complements :func:`plot_mc_trajectory` to show the magnitude of non-compliance
    rather than the rate.

    Args:
        result: A ``MonteCarloResult`` with ``step_n_violators`` populated.

    Returns:
        Matplotlib Figure.
    """
    from compute_permit_sim.schemas.batch import MonteCarloResult

    if not isinstance(result, MonteCarloResult):
        raise TypeError(f"Expected MonteCarloResult, got {type(result)}")

    fig, ax = create_figure(figsize=(7, 4))
    steps = list(range(1, len(result.step_n_violators) + 1))
    means = [s.mean for s in result.step_n_violators]
    lows = [max(0.0, s.mean - s.std) for s in result.step_n_violators]
    highs = [s.mean + s.std for s in result.step_n_violators]

    color = CHART_COLOR_MAP.get("violator", "#EF5350")
    ax.plot(steps, means, color=color, linewidth=2, label="Mean violators")
    ax.fill_between(steps, lows, highs, alpha=0.18, color=color, label="± 1 SD")
    ax.axhline(
        0,
        color="#66BB6A",
        linewidth=1,
        linestyle="--",
        alpha=0.5,
        label="Zero violators",
    )

    ax.set_xlim(1, max(steps))
    ax.set_ylim(bottom=-0.5)
    ax.set_xlabel("Simulation Step")
    ax.set_ylabel("Number of Violators")
    ax.set_title(
        _wrap(
            f"Violator Count Trajectory — {result.scenario_name} ({result.n_runs} seeds)"
        ),
        fontsize=11,
        fontweight="600",
    )
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


def plot_mc_audit_trajectory(result) -> "Figure":
    """Plot audit rate as a horizontal band across simulation steps.

    Shows the aggregate audit burden with ± 1 SD shading.
    Useful for Section 4.2 audit burden analysis.

    Args:
        result: A ``MonteCarloResult``.

    Returns:
        Matplotlib Figure.
    """
    from compute_permit_sim.schemas.batch import MonteCarloResult

    if not isinstance(result, MonteCarloResult):
        raise TypeError(f"Expected MonteCarloResult, got {type(result)}")

    fig, ax = create_figure(figsize=(7, 4))
    n_steps = len(result.step_compliance)
    steps = list(range(1, n_steps + 1))
    mean = result.audit_rate.mean
    std = result.audit_rate.std

    color = CHART_COLOR_MAP.get("audit", "#AB47BC")
    ax.axhline(mean, color=color, linewidth=2, label=f"Mean audit rate ({mean:.1%})")
    ax.fill_between(
        steps,
        [max(0.0, mean - std)] * n_steps,
        [min(1.0, mean + std)] * n_steps,
        alpha=0.18,
        color=color,
        label="± 1 SD",
    )

    ax.set_xlim(1, max(steps))
    ax.set_ylim(-0.02, min(1.05, mean + 3 * std + 0.05))
    ax.set_xlabel("Simulation Step")
    ax.set_ylabel("Audit Rate")
    ax.set_title(
        _wrap(f"Audit Rate — {result.scenario_name} ({result.n_runs} seeds)"),
        fontsize=11,
        fontweight="600",
    )
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1))
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


def plot_mc_payoff_comparison(result) -> "Figure":
    """Bar chart comparing split payoffs: compliant vs. violating labs.

    Shows mean payoff per lab‑step with 95 % CI error bars.
    Directly feeds Section 4.2 economic analysis.

    Args:
        result: A ``MonteCarloResult`` with ``payoff_compliant``
                and ``payoff_violator`` populated.

    Returns:
        Matplotlib Figure.
    """
    import math

    from compute_permit_sim.schemas.batch import MonteCarloResult

    if not isinstance(result, MonteCarloResult):
        raise TypeError(f"Expected MonteCarloResult, got {type(result)}")

    fig, ax = create_figure(figsize=(5, 4))

    labels = ["Compliant Labs", "Violating Labs"]
    means = [result.payoff_compliant.mean, result.payoff_violator.mean]
    cis = [
        result.payoff_compliant.mean - result.payoff_compliant.ci_low,
        result.payoff_violator.mean - result.payoff_violator.ci_low,
    ]
    # Replace NaN with 0 for display
    means = [0.0 if math.isnan(m) else m for m in means]
    cis = [0.0 if math.isnan(c) else c for c in cis]

    colors = [
        CHART_COLOR_MAP.get("compliant", "#42A5F5"),
        CHART_COLOR_MAP.get("violator", "#EF5350"),
    ]
    bars = ax.bar(labels, means, color=colors, width=0.45, zorder=2)
    ax.errorbar(
        labels,
        means,
        yerr=cis,
        fmt="none",
        color="#333333",
        capsize=6,
        linewidth=1.5,
        zorder=3,
    )
    for bar, m in zip(bars, means):
        ypos = (
            bar.get_height() + 0.05
            if bar.get_height() >= 0
            else bar.get_height() - 0.15
        )
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            ypos,
            f"${m:.2f}M",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="500",
        )

    ax.axhline(0, color="#999", linewidth=0.8)
    ax.set_ylabel("Avg Net Payoff per Lab-Step (M$)")
    ax.set_title(
        _wrap(f"Payoff: Compliant vs. Violating — {result.scenario_name}"),
        fontsize=11,
        fontweight="600",
    )
    ax.yaxis.grid(True, alpha=0.25, zorder=0)
    fig.tight_layout()
    return fig


def plot_sweep_curve(
    result,
    metric: str = "avg_compliance",
    reference_lines: list[tuple[float, str, str]] | None = None,
) -> "Figure":
    """Plot a 1D parameter sweep curve: param value on X, metric on Y.

    Renders the mean as a line with ± 1 SD shading. Annotates the tipping
    point (first value where compliance ≥ 95 %) if present.

    Args:
        result: A ``SweepResult`` instance.
        metric: Attribute name on ``MonteCarloResult`` to plot (default: avg_compliance).
        reference_lines: Optional list of ``(x_value, label, color)`` tuples
            for annotating known calibration points (e.g. scenario pa values).
            Each draws a vertical dotted line with a small text label.

    Returns:
        Matplotlib Figure.
    """
    from compute_permit_sim.schemas.batch import SweepResult

    if not isinstance(result, SweepResult):
        raise TypeError(f"Expected SweepResult, got {type(result)}")

    fig, ax = create_figure(figsize=(7, 4))
    xs = [pt.param_value for pt in result.points]
    metric_stats = [getattr(pt.result, metric) for pt in result.points]
    means = [s.mean for s in metric_stats]
    stds = [s.std for s in metric_stats]
    lows = [m - sd for m, sd in zip(means, stds)]
    highs = [m + sd for m, sd in zip(means, stds)]

    color = CHART_COLOR_MAP.get("compliant", "#42A5F5")
    ax.plot(xs, means, color=color, linewidth=2, marker="o", markersize=5, label="Mean")
    ax.fill_between(xs, lows, highs, alpha=0.18, color=color, label="\u00b1 1 SD")

    is_compliance = "compliance" in metric
    if is_compliance:
        ax.set_ylim(-0.05, 1.05)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1))
        ax.set_ylabel("Compliance Rate")
    else:
        ax.set_ylabel(metric.replace("_", " ").title())

    ax.set_xlabel(_wrap(result.param_label, width=40))
    ax.set_title(
        _wrap(f"Sensitivity: {result.param_label} \u2014 {result.scenario_name}"),
        fontsize=11,
        fontweight="600",
    )
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


def _fmt_param(value: float) -> str:
    """Format a swept parameter value compactly (trims trailing zeros)."""
    if abs(value) >= 1 or value == 0:
        return f"{value:g}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


class LeverSummary(NamedTuple):
    """One lever's one-at-a-time sweep reduced to its compliance extremes.

    Shared by the tornado figure and the LaTeX sensitivity table so both read
    the same numbers. ``span`` (hi - lo) is the relative-impact metric.
    """

    label: str
    range_str: str  # e.g. "70--190"
    lo: float  # min compliance over the swept range
    lo_at: float  # param value producing lo
    hi: float  # max compliance over the swept range
    hi_at: float  # param value producing hi
    span: float  # hi - lo


def lever_summary(sweep) -> LeverSummary:
    """Reduce a single-lever ``SweepResult`` to its compliance extremes.

    Args:
        sweep: A ``SweepResult`` from sweeping one lever off the baseline.

    Raises:
        TypeError: If ``sweep`` is not a ``SweepResult``.
    """
    from compute_permit_sim.schemas.batch import SweepResult

    if not isinstance(sweep, SweepResult):
        raise TypeError(f"Expected SweepResult, got {type(sweep)}")
    means = [pt.result.avg_compliance.mean for pt in sweep.points]
    values = [pt.param_value for pt in sweep.points]
    lo_i = int(np.argmin(means))
    hi_i = int(np.argmax(means))
    return LeverSummary(
        label=sweep.param_label,
        range_str=f"{min(values):g}--{max(values):g}",
        lo=means[lo_i],
        lo_at=values[lo_i],
        hi=means[hi_i],
        hi_at=values[hi_i],
        span=means[hi_i] - means[lo_i],
    )


def plot_lever_tornado(
    sweeps: list,
    baseline_compliance: float,
    title: str | None = None,
) -> "Figure":
    """Tornado plot: relative impact of each enforcement lever on compliance.

    Each lever is a horizontal bar spanning the compliance range it produces
    over its one-at-a-time sweep (all other levers held at the constructed
    baseline). Bars are sorted by span so the most impactful lever sits on top.
    A vertical reference line marks the shared baseline compliance, and each bar
    end is annotated with the parameter value that produces it.

    This is the Section 4 headline figure: one plot, every lever, read as
    "what drives compliance" off a single mid-band reference point.

    Args:
        sweeps: List of ``SweepResult`` objects, one per lever, each swept from
            the same baseline scenario.
        baseline_compliance: Mean compliance at the baseline point (0–1),
            drawn as a vertical reference line.
        title: Optional chart title.

    Returns:
        Matplotlib Figure.
    """
    # Largest span on top: sort ascending, barh fills bottom-to-top
    rows = sorted((lever_summary(s) for s in sweeps), key=lambda r: r.span)

    fig, ax = create_figure(figsize=(7.5, 0.7 * len(rows) + 1.6))
    color = CHART_COLOR_MAP.get("compliant", "#42A5F5")
    y = list(range(len(rows)))

    ax.barh(
        y,
        [r.hi - r.lo for r in rows],
        left=[r.lo for r in rows],
        height=0.6,
        color=color,
        alpha=0.55,
        edgecolor="#1A237E",
        linewidth=1.0,
        zorder=2,
    )

    ax.axvline(
        baseline_compliance,
        color="#B71C1C",
        linewidth=1.6,
        linestyle="--",
        alpha=0.9,
        zorder=3,
        label=f"Reference ({baseline_compliance * 100:.0f}%)",
    )

    for yi, r in zip(y, rows):
        ax.text(
            r.lo - 0.012,
            yi,
            _fmt_param(r.lo_at),
            ha="right",
            va="center",
            fontsize=8,
            color="#333333",
        )
        ax.text(
            r.hi + 0.012,
            yi,
            _fmt_param(r.hi_at),
            ha="left",
            va="center",
            fontsize=8,
            color="#333333",
        )
        ax.text(
            (r.lo + r.hi) / 2,
            yi,
            f"{r.span * 100:.0f} pp",
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            color="#0D1B5E",
            zorder=4,
        )

    ax.set_yticks(y)
    ax.set_yticklabels([_wrap(r.label, width=22) for r in rows], fontsize=9)
    ax.set_xlim(-0.05, 1.08)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1))
    ax.set_xlabel("Mean Compliance Rate", fontsize=11, fontweight="500")
    ax.set_title(
        _wrap(title or "Relative lever impact on compliance"),
        fontsize=12,
        fontweight="600",
    )
    ax.legend(fontsize=9, loc="lower right")
    ax.xaxis.grid(True, alpha=0.25)
    ax.yaxis.grid(False)
    fig.tight_layout()
    return fig


def plot_sweep_heatmap(
    compliance_grid: list[list[float]],
    x_values: list[float],
    y_values: list[float],
    x_param_label: str = "Base Audit Rate \u03c0\u2080",
    y_param_label: str = "Collateral K (M$)",
    x_tick_labels: list[str] | None = None,
    y_tick_labels: list[str] | None = None,
    title: str | None = None,
    highlight: tuple[float, float] | None = None,
    highlight_label: str = "Calibration",
) -> "Figure":
    """Heatmap of average compliance over a 2D parameter grid.

    Renders each cell with its mean compliance rate as a shaded colour and an
    inline percentage annotation. Designed for joint-sensitivity analysis
    (e.g. pa x K grid) and re-usable for any two-parameter sweep.

    Args:
        compliance_grid: 2D list ``[y_idx][x_idx]`` of mean compliance fractions.
        x_values: Parameter values along the x-axis (e.g. audit rates).
        y_values: Parameter values along the y-axis (e.g. collateral amounts).
        x_param_label: Human-readable x-axis label.
        y_param_label: Human-readable y-axis label.
        x_tick_labels: Optional custom tick labels for x-axis; defaults to
            auto-formatted ``x_values`` as percentages.
        y_tick_labels: Optional custom tick labels for y-axis; defaults to
            auto-formatted ``y_values`` as dollar amounts.
        title: Optional chart title.
        highlight: Optional ``(x_val, y_val)`` calibration point to outline
            with a red border.
        highlight_label: Label shown adjacent to the highlighted cell.

    Returns:
        Matplotlib Figure.
    """
    import matplotlib.patches as mpatches

    fig, ax = create_figure(figsize=(7, 5))
    data = np.array(compliance_grid)  # shape: (n_y, n_x)

    im = ax.imshow(
        data,
        aspect="auto",
        origin="lower",
        cmap="Blues",
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
    )

    # Colorbar with shared percent formatter
    cbar = fig.colorbar(
        im, ax=ax, format=matplotlib.ticker.PercentFormatter(xmax=1), shrink=0.85
    )
    cbar.set_label("Mean Compliance Rate", fontsize=10)

    # Tick labels — default to % for x (audit rate) and $M for y (collateral)
    xt_labels = x_tick_labels or [f"{v:.0%}" for v in x_values]
    yt_labels = y_tick_labels or [f"${v:.0f}M" for v in y_values]
    ax.set_xticks(range(len(x_values)))
    ax.set_xticklabels(xt_labels, fontsize=8, rotation=45, ha="right")
    ax.set_yticks(range(len(y_values)))
    ax.set_yticklabels(yt_labels, fontsize=8)

    # Per-cell compliance annotation
    for yi in range(len(y_values)):
        for xi in range(len(x_values)):
            val = float(data[yi, xi])
            text_color = "white" if val > 0.65 else "#333333"
            ax.text(
                xi,
                yi,
                f"{val:.0%}",
                ha="center",
                va="center",
                fontsize=7,
                color=text_color,
                fontweight="500",
            )

    # Optional highlight: red border around a calibration cell
    if highlight is not None:
        hx_val, hy_val = highlight
        hx_idx = min(range(len(x_values)), key=lambda i: abs(x_values[i] - hx_val))
        hy_idx = min(range(len(y_values)), key=lambda i: abs(y_values[i] - hy_val))
        rect = mpatches.FancyBboxPatch(
            (hx_idx - 0.45, hy_idx - 0.45),
            0.9,
            0.9,
            boxstyle="square,pad=0",
            linewidth=2.5,
            edgecolor=CHART_COLOR_MAP.get("violator", "#EF5350"),
            facecolor="none",
            zorder=3,
        )
        ax.add_patch(rect)
        ax.text(
            hx_idx,
            hy_idx + 0.52,
            highlight_label,
            ha="center",
            va="bottom",
            fontsize=7,
            color=CHART_COLOR_MAP.get("violator", "#EF5350"),
            fontweight="bold",
            zorder=4,
        )

    ax.set_xlabel(_wrap(x_param_label, width=40), fontsize=11, fontweight="500")
    ax.set_ylabel(_wrap(y_param_label, width=30), fontsize=11, fontweight="500")
    if title:
        ax.set_title(_wrap(title), fontsize=11, fontweight="600")

    # Suppress grid — imshow cells provide visual separation
    ax.grid(False)
    fig.tight_layout()
    return fig


def plot_compliance_violin(
    results: list,
    labels: list[str] | None = None,
) -> "Figure":
    """Violin plot of per-seed average compliance across scenarios.

    Reproduces the paper's compliance-distribution figure: one violin per
    scenario showing the density of per-seed average compliance, individual
    seeds as jittered dots, and horizontal bars at the median, P10, and P90.

    Args:
        results: List of ``MonteCarloResult`` objects run with
            ``store_raw=True`` (per-seed values are read from ``raw_seeds``).
        labels: Optional display name per result; defaults to scenario names.

    Returns:
        Matplotlib Figure.

    Raises:
        ValueError: If any result lacks raw per-seed data.
    """
    for r in results:
        if not r.raw_seeds:
            raise ValueError(
                f"MonteCarloResult '{r.scenario_name}' has no raw_seeds; "
                "run with store_raw=True."
            )

    names = labels or [r.scenario_name for r in results]
    data = [[s.avg_compliance * 100.0 for s in r.raw_seeds] for r in results]
    positions = list(range(1, len(results) + 1))

    fig, ax = create_figure(figsize=(8, 4.5))
    parts = ax.violinplot(data, positions=positions, showextrema=False, widths=0.7)
    for body in cast("list", parts["bodies"]):
        body.set_facecolor("#1A237E")
        body.set_alpha(0.25)
        body.set_zorder(2)

    rng = np.random.default_rng(0)  # presentation jitter only, not simulation RNG
    for pos, values in zip(positions, data):
        jitter = rng.uniform(-0.08, 0.08, size=len(values))
        ax.scatter(
            [pos + j for j in jitter],
            values,
            s=12,
            color="#1A237E",
            alpha=0.45,
            zorder=3,
            linewidths=0,
        )
        arr = np.asarray(values)
        for q, lw in ((50, 2.2), (10, 1.2), (90, 1.2)):
            v = float(np.percentile(arr, q))
            ax.hlines(v, pos - 0.22, pos + 0.22, color="#B71C1C", lw=lw, zorder=4)

    ax.set_xticks(positions)
    ax.set_xticklabels(names)
    ax.set_ylabel("Per-seed average compliance (%)")
    ax.set_ylim(-3, 103)
    ax.yaxis.grid(True, alpha=0.25, zorder=0)
    fig.tight_layout()
    return fig


def save_figure(fig: Figure, path: str, dpi: int = 150) -> None:
    """Save a Figure to *path* using canonical export settings.

    Single source of truth for dpi and bbox behaviour across all scripts and
    agent_workspace callers.  Never call ``fig.savefig(...)`` directly in
    workspace scripts — use this instead.

    Args:
        fig:  A ``matplotlib.figure.Figure`` returned by any plotting function.
        path: Destination file path (PNG recommended).
        dpi:  Resolution; default 150 for paper-quality output.
    """
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
