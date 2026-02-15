"""Audit targeting and deterrence frontier plots."""

import numpy as np
import pandas as pd
import solara
from matplotlib.figure import Figure

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.vis.components.charts.base import validate_dataframe
from compute_permit_sim.vis.constants import CHART_COLOR_MAP


@solara.component
def AuditTargetingPlot(agents_df: pd.DataFrame | None):
    """Bar chart showing audit rates by compliance status.

    Measures the effectiveness of audit targeting: do compliant or
    non-compliant firms get audited more?
    """
    if not validate_dataframe(
        agents_df,
        [ColumnNames.IS_COMPLIANT, ColumnNames.WAS_AUDITED],
        "Missing required columns for audit plot.",
    ):
        solara.Markdown("No data for audit targeting plot.")
        return

    compliant_agents = agents_df[agents_df[ColumnNames.IS_COMPLIANT]]
    noncompliant_agents = agents_df[~agents_df[ColumnNames.IS_COMPLIANT]]

    compliant_audit_rate = (
        compliant_agents[ColumnNames.WAS_AUDITED].mean()
        if len(compliant_agents) > 0
        else 0
    )
    noncompliant_audit_rate = (
        noncompliant_agents[ColumnNames.WAS_AUDITED].mean()
        if len(noncompliant_agents) > 0
        else 0
    )

    fig = Figure(figsize=(5, 4))
    ax = fig.subplots()

    categories = ["Compliant", "Non-Compliant"]
    rates = [compliant_audit_rate * 100, noncompliant_audit_rate * 100]
    colors = ["#4CAF50", "#F44336"]

    bars = ax.bar(categories, rates, color=colors, alpha=0.8, edgecolor="black")

    for bar, rate in zip(bars, rates):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{rate:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_ylabel("Audit Rate (%)")
    ax.set_title("Audit Targeting Effectiveness")
    ax.set_ylim(0, max(rates) * 1.2 if max(rates) > 0 else 10)
    ax.grid(True, alpha=0.3, axis="y")

    n_compliant = len(compliant_agents)
    n_noncompliant = len(noncompliant_agents)
    ax.text(
        0.02,
        0.98,
        f"n={n_compliant} compliant, {n_noncompliant} non-compliant",
        transform=ax.transAxes,
        fontsize=8,
        verticalalignment="top",
        alpha=0.7,
    )
    fig.tight_layout()
    solara.FigureMatplotlib(fig)


@solara.component
def LabDecisionPlot(agents_df: pd.DataFrame | None, audit_prob: float, penalty: float):
    """Scatter plot of Economic Value vs Risk Profile with Deterrence Frontier.

    The indifference line shows the boundary where V * R = P * (1 - p_eff).
    Agents below the line are deterred; above are willing to cheat.
    """
    if not validate_dataframe(
        agents_df,
        [
            ColumnNames.ECONOMIC_VALUE,
            ColumnNames.RISK_PROFILE,
            ColumnNames.IS_COMPLIANT,
        ],
        "Missing data for decision plot.",
    ):
        solara.Markdown(
            "Missing data for decision plot (need economic_value/risk_profile)."
        )
        return

    fig = Figure(figsize=(6, 5), dpi=100)
    ax = fig.subplots()

    x = agents_df[ColumnNames.ECONOMIC_VALUE]
    y = agents_df[ColumnNames.RISK_PROFILE]
    colors = agents_df[ColumnNames.IS_COMPLIANT].map(
        {True: CHART_COLOR_MAP["green"], False: CHART_COLOR_MAP["red"]}
    )

    ax.scatter(x, y, c=colors, alpha=0.7, edgecolors="w", s=80)

    if penalty > 0 and audit_prob > 0:
        x_line = np.linspace(x.min(), x.max(), 100)
        y_line = x_line / (penalty * audit_prob)
        ax.plot(x_line, y_line, color="gray", linestyle="--", label="Indifference Line")

    ax.set_xlabel("Economic Value (Incentive)")
    ax.set_ylabel("Risk Profile (Sensitivity)")
    ax.set_title("Deterrence Frontier")
    ax.grid(True, alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Only show legend if we plotted the line (which has a label)
    if penalty > 0 and audit_prob > 0:
        ax.legend()
    solara.FigureMatplotlib(fig)
