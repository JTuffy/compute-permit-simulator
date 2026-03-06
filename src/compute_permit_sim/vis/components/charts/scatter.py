"""Scatter and distribution chart components — step-level and aggregate modes.

Each component accepts a ``mode`` parameter (``"aggregate"`` or ``"step"``) and
renders the same chart type with data appropriate for that mode:

- ``mode="step"`` — renders a single-step snapshot from ``agents_df``
- ``mode="aggregate"`` — renders a full-run aggregate from ``steps``

Titles automatically reflect the active mode.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
import solara

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.vis.components.charts.base import validate_dataframe
from compute_permit_sim.vis.components.charts.expandable import ExpandableChart
from compute_permit_sim.vis.constants import OUTCOME_COLORS
from compute_permit_sim.vis.plotting import (
    create_figure,
    plot_audit_source_distribution,
    plot_compliance_distribution,
    plot_scatter,
)
from compute_permit_sim.vis.transforms import (
    aggregate_compliance_distribution,
    aggregate_risk_scatter,
    classify_agent_outcome,
)


@solara.component
def RiskScatterPlot(
    mode: Literal["aggregate", "step"],
    agents_df: pd.DataFrame | None = None,
    steps: list | None = None,
) -> None:
    """Scatter of Reported (X) vs True (Y) compute usage, colored by compliance.

    In step mode: per-agent snapshot for the current step.
    In aggregate mode: all (step, lab) observations across the full run.
    Points on the dashed y=x line are perfectly honest reporters.
    Points above it used more compute than reported (cheating).
    """
    if mode == "step":
        if not validate_dataframe(
            agents_df,
            [ColumnNames.REPORTED_TRAINING_FLOPS, ColumnNames.USED_TRAINING_FLOPS],
        ):
            solara.Markdown("*No data for scatter plot.*")
            return

        assert agents_df is not None
        fig, ax = plot_scatter(
            agents_df,
            ColumnNames.REPORTED_TRAINING_FLOPS,
            ColumnNames.USED_TRAINING_FLOPS,
            "Risk Design: True vs Reported (This Step)",
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
        ExpandableChart(fig)

    else:
        # Aggregate mode — pool all (step, agent) observations
        if not steps:
            solara.Markdown("*No step data.*")
            return
        df = aggregate_risk_scatter(steps)
        if df.empty:
            solara.Markdown("*No agent data.*")
            return

        x_col = ColumnNames.REPORTED_TRAINING_FLOPS
        y_col = ColumnNames.USED_TRAINING_FLOPS
        if x_col not in df.columns or y_col not in df.columns:
            solara.Markdown("*Missing FLOPs columns.*")
            return

        fig, ax = create_figure(figsize=(6, 4))

        has_status = ColumnNames.IS_COMPLIANT in df.columns
        if has_status:
            colors = [
                (
                    OUTCOME_COLORS["Caught"]
                    if row.get(ColumnNames.WAS_CAUGHT, False)
                    else (
                        OUTCOME_COLORS["Uncaught"]
                        if not row[ColumnNames.IS_COMPLIANT]
                        else OUTCOME_COLORS["Compliant"]
                    )
                )
                for _, row in df.iterrows()
            ]
        else:
            colors = [OUTCOME_COLORS["Compliant"]] * len(df)

        ax.scatter(
            df[x_col],
            df[y_col],
            c=colors,
            alpha=0.55,
            s=28,
            edgecolors="white",
            linewidths=0.3,
        )

        max_val = max(df[x_col].max(), df[y_col].max()) if not df.empty else 1.0
        ax.plot(
            [0, max_val],
            [0, max_val],
            "k--",
            alpha=0.4,
            linewidth=1.2,
            label="Honesty (y=x)",
        )

        n_steps = df["step"].nunique() if "step" in df.columns else len(steps)
        ax.set_xlabel("Reported FLOPs (r)", fontsize=10)
        ax.set_ylabel("True FLOPs (q)", fontsize=10)
        ax.set_title(
            f"Risk Design: Used vs Reported (Full Run)\n"
            f"(N={len(df)} observations, {n_steps} steps)",
            fontsize=11,
            fontweight="600",
        )
        ax.legend(fontsize=7, loc="upper left")
        fig.tight_layout()
        ExpandableChart(fig)


@solara.component
def ComplianceDistributionPlot(
    mode: Literal["aggregate", "step"],
    agents_df: pd.DataFrame | None = None,
    steps: list | None = None,
) -> None:
    """Bar chart: Compliant / Uncaught / per-source Caught counts.

    In step mode: snapshot for the current step from ``agents_df``.
    In aggregate mode: cumulative totals across the full run from ``steps``.
    """
    if mode == "step":
        if not validate_dataframe(
            agents_df,
            [ColumnNames.IS_COMPLIANT, ColumnNames.WAS_CAUGHT],
        ):
            solara.Markdown("*No compliance data.*")
            return
        assert agents_df is not None
        df = classify_agent_outcome(agents_df)
        fig = plot_compliance_distribution(
            df, title="Compliance Distribution (This Step)"
        )
        ExpandableChart(fig)

    else:
        # Aggregate mode
        if not steps:
            solara.Markdown("*No step data.*")
            return
        df = aggregate_compliance_distribution(steps)
        if df.empty:
            solara.Markdown("*No agent outcome data.*")
            return
        fig = plot_compliance_distribution(
            df, title="Compliance Distribution (Full Run)"
        )
        ExpandableChart(fig)


@solara.component
def AuditSourcePlot(
    mode: Literal["aggregate", "step"],
    agents_df: pd.DataFrame | None = None,
    steps: list | None = None,
) -> None:
    """Bar chart: caught labs by detection channel (direct/backcheck/whistleblower/monitoring).

    In step mode: snapshot for the current step.
    In aggregate mode: cumulative totals across the full run.
    """
    if mode == "step":
        if not validate_dataframe(agents_df, [ColumnNames.WAS_CAUGHT]):
            solara.Markdown("*No audit data.*")
            return
        assert agents_df is not None
        df = classify_agent_outcome(agents_df)
        caught_only = df[df["outcome"] == "Caught"]
        fig = plot_audit_source_distribution(
            caught_only, title="Caught by Channel (This Step)"
        )
        ExpandableChart(fig)

    else:
        # Aggregate mode
        if not steps:
            solara.Markdown("*No step data.*")
            return
        df = aggregate_compliance_distribution(steps)
        if df.empty:
            solara.Markdown("*No agent data.*")
            return
        fig = plot_audit_source_distribution(df, title="Caught by Channel (Full Run)")
        ExpandableChart(fig)
