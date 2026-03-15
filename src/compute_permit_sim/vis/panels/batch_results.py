"""Batch results panel — shown in the right pane after a batch/sweep run.

All shared display primitives (MetricChip, fig_to_png, DownloadCSV, …) come
from ``vis/components/results.py`` — the single source of truth for result
panel UI atoms across basic, Monte Carlo, and sweep views.
"""

from __future__ import annotations

from typing import Any

import solara

from compute_permit_sim.vis.components.charts.expandable import ExpandableChart
from compute_permit_sim.vis.components.dialogs import RunConfigDialog
from compute_permit_sim.vis.components.results import (
    DownloadCSV,
    DownloadExcel,
    DownloadJSON,
    MetricChip,
    ResultsActions,
)
from compute_permit_sim.vis.state.run_state import grid_run, mc_run, sweep_run

# ---------------------------------------------------------------------------
# Monte Carlo results
# ---------------------------------------------------------------------------


@solara.component
def _MCResultsView() -> Any:
    from compute_permit_sim.vis.export import (
        export_monte_carlo_to_csv,
        export_monte_carlo_to_excel,
    )
    from compute_permit_sim.vis.plotting import (
        plot_mc_audit_trajectory,
        plot_mc_payoff_comparison,
        plot_mc_trajectory,
        plot_mc_violator_trajectory,
    )

    result = mc_run.value.result
    if result is None:
        solara.Text("No Monte Carlo result to display.")
        return

    safe = result.scenario_name.lower().replace(" ", "_")

    # Figures computed once; ExpandableChart renders them inline + handles PNG download internally
    fig_comp = plot_mc_trajectory(result)
    fig_viol = plot_mc_violator_trajectory(result)
    fig_audit = plot_mc_audit_trajectory(result)
    fig_pay = plot_mc_payoff_comparison(result)

    with solara.Column(classes=["analysis-panel"]):
        # ── SECTION 1 : Summary card (mirrors AnalysisSummary) ──────────
        with solara.Card("Summary", style="margin-bottom: 12px;"):
            with solara.Row(
                style="align-items: center; justify-content: space-between; flex-wrap: wrap;"
            ):
                # Metric chips
                with solara.Row(style="gap: 24px; flex-wrap: wrap; flex: 1;"):
                    MetricChip("Scenario", result.scenario_name)
                    MetricChip("Seeds", str(result.n_runs))
                    MetricChip(
                        "Avg Compliance",
                        f"{result.avg_compliance.mean:.1%} \u00b1 {result.avg_compliance.std:.1%}",
                    )
                    MetricChip(
                        "P10\u2013P90",
                        f"[{result.p10_compliance:.1%}\u2013{result.p90_compliance:.1%}]",
                    )
                    MetricChip(
                        "Full Compliance",
                        f"{result.pct_runs_full_compliance:.0%} of seeds",
                    )
                    MetricChip("Audit Rate", f"{result.audit_rate.mean:.1%}")

                with ResultsActions():
                    RunConfigDialog(
                        config=result.config,
                        title=f"MC Run: {result.id}",
                        batch_summary=(
                            f"**{result.n_runs} Monte Carlo runs** · {result.scenario_name}  \n"
                            f"Avg compliance: **{result.avg_compliance.mean:.1%}**"
                            f" ±{result.avg_compliance.std:.1%}  \n"
                            f"P10\u2013P90: {result.p10_compliance:.0%} \u2013 {result.p90_compliance:.0%}"
                        ),
                    )
                    DownloadCSV(
                        "Download summary CSV",
                        lambda r=result: export_monte_carlo_to_csv([r], output_path=""),  # type: ignore[misc]
                        f"mc_summary_{safe}.csv",
                    )
                    DownloadExcel(
                        "Download Excel workbook",
                        lambda r=result: export_monte_carlo_to_excel(r, output_path=""),  # type: ignore[misc]
                        f"mc_{safe}.xlsx",
                    )
                    DownloadJSON(
                        "Download config JSON (for reproducibility)",
                        lambda r=result: r.config.model_dump_json(indent=2).encode(
                            "utf-8"
                        ),  # type: ignore[misc]
                        f"mc_config_{safe}.json",
                    )

        with solara.Card("Results", style="margin-top: 0;"):
            # Row 1: compliance, violator, audit — 3-column matching basic results panel
            with solara.Columns([1, 1, 1]):
                with solara.Column():
                    ExpandableChart(
                        fig_comp, download_filename=f"mc_compliance_{safe}.png"
                    )
                with solara.Column():
                    ExpandableChart(
                        fig_viol, download_filename=f"mc_violators_{safe}.png"
                    )
                with solara.Column():
                    ExpandableChart(fig_audit, download_filename=f"mc_audit_{safe}.png")
            # Row 2: payoff (reserved slots align with basic layout)
            with solara.Columns([1, 1, 1]):
                with solara.Column():
                    ExpandableChart(fig_pay, download_filename=f"mc_payoff_{safe}.png")
                with solara.Column():
                    pass  # reserved
                with solara.Column():
                    pass  # reserved

        # ── SECTION 3 : Stats table ──────────────────────────────────────
        with solara.Card("Statistics", style="margin-top: 0;"):
            rows: list[tuple[str, ...]] = [
                ("Metric", "Mean", "SD", "P10", "P90"),
                (
                    "Avg Compliance",
                    f"{result.avg_compliance.mean:.1%}",
                    f"{result.avg_compliance.std:.1%}",
                    f"{result.p10_compliance:.1%}",
                    f"{result.p90_compliance:.1%}",
                ),
                (
                    "Final Compliance",
                    f"{result.final_compliance.mean:.1%}",
                    f"{result.final_compliance.std:.1%}",
                    "\u2014",
                    "\u2014",
                ),
                (
                    "Market Price (M$)",
                    f"{result.avg_price.mean:.2f}",
                    f"{result.avg_price.std:.2f}",
                    "\u2014",
                    "\u2014",
                ),
                (
                    "Net Payoff (M$)",
                    f"{result.avg_net_payoff.mean:.2f}",
                    f"{result.avg_net_payoff.std:.2f}",
                    "\u2014",
                    "\u2014",
                ),
                (
                    "Payoff Compliant (M$)",
                    f"{result.payoff_compliant.mean:.2f}",
                    f"{result.payoff_compliant.std:.2f}",
                    "\u2014",
                    "\u2014",
                ),
                (
                    "Payoff Violator (M$)",
                    f"{result.payoff_violator.mean:.2f}",
                    f"{result.payoff_violator.std:.2f}",
                    "\u2014",
                    "\u2014",
                ),
                (
                    "Audit Rate",
                    f"{result.audit_rate.mean:.1%}",
                    f"{result.audit_rate.std:.1%}",
                    "\u2014",
                    "\u2014",
                ),
                (
                    "False Positive Rate",
                    f"{result.false_positive_rate.mean:.1%}",
                    f"{result.false_positive_rate.std:.1%}",
                    "\u2014",
                    "\u2014",
                ),
                (
                    "Detection Rate",
                    f"{result.detection_rate.mean:.1%}",
                    f"{result.detection_rate.std:.1%}",
                    "\u2014",
                    "\u2014",
                ),
                (
                    "% Seeds Full Compliance",
                    f"{result.pct_runs_full_compliance:.0%}",
                    "\u2014",
                    "\u2014",
                    "\u2014",
                ),
            ]
            header = "| " + " | ".join(rows[0]) + " |"
            sep = "|" + "|".join(["---"] * len(rows[0])) + "|"
            body = "\n".join("| " + " | ".join(r) + " |" for r in rows[1:])
            solara.Markdown("\n".join([header, sep, body]))


# ---------------------------------------------------------------------------
# Sweep results
# ---------------------------------------------------------------------------


@solara.component
def _SweepResultsView() -> Any:
    from compute_permit_sim.vis.export import export_sweep_to_csv, export_sweep_to_excel
    from compute_permit_sim.vis.plotting import plot_sweep_curve

    result = sweep_run.value.result
    if result is None:
        solara.Text("No sweep result to display.")
        return

    safe_p = result.param_path.replace(".", "_")
    safe_s = result.scenario_name.lower().replace(" ", "_")
    tp = result.tipping_point()

    # Figure computed once; ExpandableChart handles inline render + PNG download internally
    fig = plot_sweep_curve(result, metric="avg_compliance")

    with solara.Column(classes=["analysis-panel"]):
        with solara.Card("Summary", style="margin-bottom: 12px;"):
            with solara.Row(
                style="align-items: center; justify-content: space-between; flex-wrap: wrap;"
            ):
                with solara.Row(style="gap: 24px; flex-wrap: wrap; flex: 1;"):
                    MetricChip("Scenario", result.scenario_name)
                    MetricChip("Parameter", result.param_label)
                    MetricChip("Points", str(len(result.points)))
                    MetricChip(
                        "Tipping point",
                        f"{tp:.4f}" if tp is not None else "not reached",
                    )
                with ResultsActions():
                    RunConfigDialog(
                        config=result.config,
                        title=f"Sweep Run: {result.id}",
                        batch_summary=(
                            f"**{len(result.points)}-point sweep** · {result.scenario_name}  \n"
                            f"Parameter: **{result.param_label}**  \n"
                            f"Tipping point: {f'tp≈{tp:.3f}' if tp is not None else 'not reached'}"
                        ),
                    )
                    DownloadCSV(
                        "Download sweep CSV",
                        lambda r=result: export_sweep_to_csv(r, output_path=""),  # type: ignore[misc]
                        f"sweep_{safe_s}_{safe_p}.csv",
                    )
                    DownloadExcel(
                        "Download Excel workbook",
                        lambda r=result: export_sweep_to_excel(r, output_path=""),  # type: ignore[misc]
                        f"sweep_{safe_s}_{safe_p}.xlsx",
                    )
                    DownloadJSON(
                        "Download config JSON (for reproducibility)",
                        lambda r=result: r.config.model_dump_json(indent=2).encode(
                            "utf-8"
                        ),  # type: ignore[misc]
                        f"sweep_config_{safe_s}_{safe_p}.json",
                    )

        with solara.Card("Results", style="margin-top: 0;"):
            ExpandableChart(fig, download_filename=f"sweep_{safe_s}_{safe_p}.png")

        # ── Per-point table ──────────────────────────────────────────────
        with solara.Card("Per-Point Summary", style="margin-top: 0;"):
            rows: list[tuple[str, ...]] = [
                (
                    "Param Value",
                    "Avg Compliance",
                    "SD",
                    "P10\u2013P90",
                    "Audit Rate",
                    "Net Payoff (M$)",
                )
            ]
            for pt in result.points:
                r = pt.result
                rows.append(
                    (
                        f"{pt.param_value:.4f}",
                        f"{r.avg_compliance.mean:.1%}",
                        f"{r.avg_compliance.std:.1%}",
                        f"[{r.p10_compliance:.1%}\u2013{r.p90_compliance:.1%}]",
                        f"{r.audit_rate.mean:.1%}",
                        f"{r.avg_net_payoff.mean:.2f}",
                    )
                )
            header = "| " + " | ".join(rows[0]) + " |"
            sep = "|" + "|".join(["---"] * len(rows[0])) + "|"
            body = "\n".join("| " + " | ".join(r) + " |" for r in rows[1:])
            solara.Markdown("\n".join([header, sep, body]))


# ---------------------------------------------------------------------------
# Grid sweep results
# ---------------------------------------------------------------------------


@solara.component
def _GridSweepResultsView() -> Any:
    from compute_permit_sim.vis.export import (
        export_grid_sweep_to_csv,
        export_grid_sweep_to_excel,
    )
    from compute_permit_sim.vis.plotting import plot_sweep_heatmap

    result = grid_run.value.result
    if result is None:
        solara.Text("No grid sweep result to display.")
        return

    safe_s = result.scenario_name.lower().replace(" ", "_")
    safe_x = result.param_x_path.replace(".", "_")
    safe_y = result.param_y_path.replace(".", "_")

    fig = plot_sweep_heatmap(
        compliance_grid=result.grid,
        x_values=result.x_values,
        y_values=result.y_values,
        x_param_label=result.param_x_label,
        y_param_label=result.param_y_label,
        title=f"Compliance Heatmap — {result.scenario_name}",
    )

    with solara.Column(classes=["analysis-panel"]):
        with solara.Card("Summary", style="margin-bottom: 12px;"):
            with solara.Row(
                style="align-items: center; justify-content: space-between; flex-wrap: wrap;"
            ):
                with solara.Row(style="gap: 24px; flex-wrap: wrap; flex: 1;"):
                    MetricChip("Scenario", result.scenario_name)
                    MetricChip("X-axis", result.param_x_label)
                    MetricChip("Y-axis", result.param_y_label)
                    MetricChip(
                        "Grid size",
                        f"{len(result.x_values)}\u00d7{len(result.y_values)}",
                    )
                    MetricChip("Seeds per cell", str(result.n_runs))
                    MetricChip(
                        "Compliance range",
                        f"{result.compliance_min:.1%}\u2013{result.compliance_max:.1%}",
                    )

                with ResultsActions():
                    RunConfigDialog(
                        config=result.config,
                        title=f"Grid Sweep: {result.id}",
                        batch_summary=(
                            f"**{len(result.x_values)}\u00d7{len(result.y_values)} grid sweep**"
                            f" \u00b7 {result.scenario_name}  \n"
                            f"X: **{result.param_x_label}**  \n"
                            f"Y: **{result.param_y_label}**  \n"
                            f"Compliance range: "
                            f"{result.compliance_min:.1%}\u2013{result.compliance_max:.1%}"
                        ),
                    )
                    DownloadCSV(
                        "Download grid CSV",
                        lambda r=result: export_grid_sweep_to_csv(  # type: ignore[misc]
                            r, output_path=""
                        ),
                        f"grid_{safe_s}_{safe_x}_x_{safe_y}.csv",
                    )
                    DownloadExcel(
                        "Download Excel workbook",
                        lambda r=result: export_grid_sweep_to_excel(  # type: ignore[misc]
                            r, output_path=""
                        ),
                        f"grid_{safe_s}_{safe_x}_x_{safe_y}.xlsx",
                    )
                    DownloadJSON(
                        "Download config JSON (for reproducibility)",
                        lambda r=result: r.config.model_dump_json(  # type: ignore[misc]
                            indent=2
                        ).encode("utf-8"),
                        f"grid_config_{safe_s}.json",
                    )

        with solara.Card("Results", style="margin-top: 0;"):
            ExpandableChart(
                fig,
                download_filename=f"grid_{safe_s}_{safe_x}_x_{safe_y}.png",
            )

        with solara.Card("Per-Cell Compliance", style="margin-top: 0;"):
            # Header: blank corner + x-axis values
            x_hdrs = [result.param_x_label] + [f"{x:.4g}" for x in result.x_values]
            header = "| " + " | ".join(x_hdrs) + " |"
            sep = "|" + "|".join(["---"] * len(x_hdrs)) + "|"
            # One row per y value — compliance as percentage
            data_rows = []
            for y_idx, y in enumerate(result.y_values):
                cells = [f"{y:.4g}"] + [
                    f"{result.grid[y_idx][x_idx]:.1%}"
                    for x_idx in range(len(result.x_values))
                ]
                data_rows.append("| " + " | ".join(cells) + " |")
            y_label_row = f"*Y: {result.param_y_label}*"
            solara.Markdown(y_label_row)
            solara.Markdown("\n".join([header, sep] + data_rows))


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


@solara.component
def BatchResultsPanel() -> Any:
    """Right-pane panel for batch results.

    Reads result directly from mc_run / sweep_run / grid_run RunState singletons.
    Page-level state machine in page.py ensures this panel is only rendered
    when a result is ready — no spinner gate needed here.
    """
    mc = mc_run.value
    sw = sweep_run.value
    gr = grid_run.value

    if mc.is_ready and mc.result is not None:
        _MCResultsView()
    elif sw.is_ready and sw.result is not None:
        _SweepResultsView()
    elif gr.is_ready and gr.result is not None:
        _GridSweepResultsView()
    else:
        solara.Text("No batch results to display.")
