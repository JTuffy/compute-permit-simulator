"""Longitudinal and sim-level chart components.

All components aggregate data across the full simulation run rather than
a single step, providing a companion "full run" view to each step-wise chart.

All components use ExpandableChart for consistent click-to-zoom UX.
"""

from __future__ import annotations

import solara

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.vis.components.charts.expandable import ExpandableChart
from compute_permit_sim.vis.constants import OUTCOME_COLORS
from compute_permit_sim.vis.plotting import (
    create_figure,
    plot_audit_source_distribution,
    plot_audit_targeting,
    plot_compliance_distribution,
)
from compute_permit_sim.vis.transforms import (
    aggregate_audit_targeting,
    aggregate_compliance_distribution,
    aggregate_risk_scatter,
)

# ---------------------------------------------------------------------------
# Sim-level aggregate components (mirror of the 3 step-wise charts)
# ---------------------------------------------------------------------------


@solara.component
def SimRiskScatterPlot(steps: list) -> None:
    """Scatter of Used vs Reported FLOPs coloured by compliance outcome.

    Aggregates every (step, lab) observation across the full run.
    Green = compliant, Red = non-compliant/uncaught, Black = caught.
    Matches the same colour scheme as the step-wise scatter.
    A tight diagonal cluster means consistently honest reporting;
    scatter above y=x reveals systematic under-reporting.
    """
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

    # Colour by compliance outcome — matches the step-wise scatter exactly
    has_status = (
        ColumnNames.IS_COMPLIANT in df.columns and ColumnNames.WAS_CAUGHT in df.columns
    )
    if has_status:
        colors = []
        for _, row in df.iterrows():
            if row.get(ColumnNames.WAS_CAUGHT, False):
                colors.append(OUTCOME_COLORS["Caught"])
            elif not row[ColumnNames.IS_COMPLIANT]:
                colors.append(OUTCOME_COLORS["Uncaught"])
            else:
                colors.append(OUTCOME_COLORS["Compliant"])
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
        f"Risk Design: Used vs Reported\n(N={len(df)} observations, {n_steps} steps)",
        fontsize=11,
        fontweight="600",
    )
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    ExpandableChart(fig)


@solara.component
def SimAuditTargetingPlot(steps: list) -> None:
    """Audit rate by compliance group, aggregated over the full run.

    Parallel to the step-wise Audit Targeting chart but shows the overall
    rate across all steps — answering whether enforcement is systematically
    targeting non-compliant labs or auditing everyone indiscriminately.
    """
    if not steps:
        solara.Markdown("*No step data.*")
        return
    stats = aggregate_audit_targeting(steps)
    fig = plot_audit_targeting(
        compliant_rate=stats["compliant_rate"],
        noncompliant_rate=stats["noncompliant_rate"],
        n_compliant=stats["compliant_total"],
        n_noncompliant=stats["noncompliant_total"],
        title="Audit Targeting (Full Run)",
    )
    ExpandableChart(fig)


@solara.component
def SimComplianceDistributionPlot(steps: list) -> None:
    """Compliance outcome distribution (Compliant / Uncaught / Caught) across all steps.

    Parallel to the step-wise Compliance Distribution but aggregated so you
    see cumulative counts. Caught labs are sub-divided by detection channel
    (DIRECT / BACKCHECK / WHISTLEBLOWER / MONITORING).
    """
    if not steps:
        solara.Markdown("*No step data.*")
        return
    df = aggregate_compliance_distribution(steps)
    if df.empty:
        solara.Markdown("*No agent outcome data.*")
        return
    fig = plot_compliance_distribution(df, title="Compliance Distribution (Full Run)")
    ExpandableChart(fig)


@solara.component
def SimAuditSourcePlot(steps: list) -> None:
    """Caught labs broken out by detection channel, aggregated over the full run.

    Shows how enforcement is finding violators — direct inspections,
    back-checks, whistleblower tips, or ongoing monitoring — across all steps.
    Parallel to the step-wise AuditSourcePlot but cumulative.
    """
    if not steps:
        solara.Markdown("*No step data.*")
        return
    df = aggregate_compliance_distribution(steps)
    if df.empty:
        solara.Markdown("*No agent data.*")
        return
    fig = plot_audit_source_distribution(df, title="Caught by Channel (Full Run)")
    ExpandableChart(fig)
