"""Batch results panel — shown in the right pane after a batch/sweep run.

Layout deliberately mirrors ``panels/analysis.py``:
- ``solara.Card("Summary")`` with ``_MetricChip`` row + icon action buttons
- Charts rendered inside ``solara.Card("Results")``
- Same ``mdi-*`` icon-only ``FileDownload`` buttons as ``summary.py``

No status text below the run button — success is evident from results appearing here.
"""

from __future__ import annotations

import io
from typing import Any

import solara

from compute_permit_sim.vis.state.run_state import mc_run, sweep_run

# ---------------------------------------------------------------------------
# Shared helpers (identical to summary.py private helpers)
# ---------------------------------------------------------------------------


@solara.component
def _MetricChip(label: str, value: str) -> None:
    """Small metric display chip — mirrors summary.py."""
    solara.Markdown(f"**{label}:** {value}", style="white-space: nowrap;")


def _fig_png(fig: Any) -> bytes:
    """Render a Matplotlib figure to PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    buf.seek(0)
    return buf.read()


def _dl_csv(tooltip: str, data_fn: Any, filename: str) -> None:
    """Icon-only CSV FileDownload matching summary.py export buttons."""
    with solara.Tooltip(tooltip):
        with solara.FileDownload(data=data_fn, filename=filename, mime_type="text/csv"):
            solara.Button(icon_name="mdi-file-delimited-outline", icon=True, small=True)


def _dl_png(tooltip: str, data_fn: Any, filename: str) -> None:
    """Icon-only PNG FileDownload."""
    with solara.Tooltip(tooltip):
        with solara.FileDownload(
            data=data_fn, filename=filename, mime_type="image/png"
        ):
            solara.Button(icon_name="mdi-file-image-outline", icon=True, small=True)


def _dl_tex(tooltip: str, data_fn: Any, filename: str) -> None:
    """Icon-only LaTeX FileDownload."""
    with solara.Tooltip(tooltip):
        with solara.FileDownload(
            data=data_fn, filename=filename, mime_type="text/plain"
        ):
            solara.Button(icon_name="mdi-code-braces", icon=True, small=True)


# ---------------------------------------------------------------------------
# Monte Carlo results
# ---------------------------------------------------------------------------


@solara.component
def _MCResultsView() -> Any:
    from compute_permit_sim.vis.export import (
        export_mc_per_seed_to_csv,
        export_mc_trajectory_to_csv,
        export_monte_carlo_to_csv,
        export_monte_carlo_to_latex,
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

    # Render figures once so downloads re-use the same bytes
    fig_comp = plot_mc_trajectory(result)
    fig_viol = plot_mc_violator_trajectory(result)
    fig_audit = plot_mc_audit_trajectory(result)
    fig_pay = plot_mc_payoff_comparison(result)
    png_comp = _fig_png(fig_comp)
    png_viol = _fig_png(fig_viol)
    png_audit = _fig_png(fig_audit)
    png_pay = _fig_png(fig_pay)

    with solara.Column(classes=["analysis-panel"]):
        # ── SECTION 1 : Summary card (mirrors AnalysisSummary) ──────────
        with solara.Card("Summary", style="margin-bottom: 12px;"):
            with solara.Row(
                style="align-items: center; justify-content: space-between; flex-wrap: wrap;"
            ):
                # Metric chips
                with solara.Row(style="gap: 24px; flex-wrap: wrap; flex: 1;"):
                    _MetricChip("Scenario", result.scenario_name)
                    _MetricChip("Seeds", str(result.n_runs))
                    _MetricChip(
                        "Avg Compliance",
                        f"{result.avg_compliance.mean:.1%} \u00b1 {result.avg_compliance.std:.1%}",
                    )
                    _MetricChip(
                        "P10\u2013P90",
                        f"[{result.p10_compliance:.1%}\u2013{result.p90_compliance:.1%}]",
                    )
                    _MetricChip(
                        "Full Compliance",
                        f"{result.pct_runs_full_compliance:.0%} of seeds",
                    )
                    _MetricChip("Audit Rate", f"{result.audit_rate.mean:.1%}")

                # Action buttons — ordered to match basic panel (CSV → trajectory → per-seed → LaTeX)
                with solara.Row(style="gap: 4px; align-items: center;"):
                    _dl_csv(
                        "Download summary CSV",
                        lambda r=result: export_monte_carlo_to_csv([r], output_path=""),
                        f"mc_summary_{safe}.csv",
                    )
                    _dl_csv(
                        "Download trajectory CSV",
                        lambda r=result: export_mc_trajectory_to_csv(r, output_path=""),
                        f"mc_trajectory_{safe}.csv",
                    )
                    if result.raw_seeds:
                        _dl_csv(
                            "Download per-seed CSV",
                            lambda r=result: export_mc_per_seed_to_csv(
                                r, output_path=""
                            ),
                            f"mc_per_seed_{safe}.csv",
                        )
                    _dl_tex(
                        "Download LaTeX table",
                        lambda r=result: export_monte_carlo_to_latex([r]).encode(
                            "utf-8"
                        ),
                        f"mc_table_{safe}.tex",
                    )

        # ── SECTION 2 : Results card (mirrors ResultsContent) ───────────
        with solara.Card("Results", style="margin-top: 0;"):
            # Charts — each with an inline PNG download row attached above the image
            with solara.Column(style="gap: 8px;"):
                for png_bytes, tooltip, fname in [
                    (png_comp, "Compliance trajectory", f"mc_compliance_{safe}.png"),
                    (png_viol, "Violator count trajectory", f"mc_violators_{safe}.png"),
                    (png_audit, "Audit rate chart", f"mc_audit_{safe}.png"),
                    (png_pay, "Payoff comparison", f"mc_payoff_{safe}.png"),
                ]:
                    with solara.Column(style="gap: 0;"):
                        with solara.Row(
                            style="justify-content: flex-end; margin-bottom: 2px;"
                        ):
                            _dl_png(tooltip, lambda p=png_bytes: p, fname)
                        solara.Image(png_bytes)

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
    from compute_permit_sim.vis.export import export_sweep_to_csv
    from compute_permit_sim.vis.plotting import plot_sweep_curve

    result = sweep_run.value.result
    if result is None:
        solara.Text("No sweep result to display.")
        return

    safe_p = result.param_path.replace(".", "_")
    safe_s = result.scenario_name.lower().replace(" ", "_")
    tp = result.tipping_point()

    fig = plot_sweep_curve(result, metric="avg_compliance")
    png = _fig_png(fig)

    with solara.Column(classes=["analysis-panel"]):
        # ── Summary card ────────────────────────────────────────────────
        with solara.Card("Summary", style="margin-bottom: 12px;"):
            with solara.Row(
                style="align-items: center; justify-content: space-between; flex-wrap: wrap;"
            ):
                with solara.Row(style="gap: 24px; flex-wrap: wrap; flex: 1;"):
                    _MetricChip("Scenario", result.scenario_name)
                    _MetricChip("Parameter", result.param_label)
                    _MetricChip("Points", str(len(result.points)))
                    _MetricChip(
                        "Tipping point",
                        f"{tp:.4f}" if tp is not None else "not reached",
                    )
                with solara.Row(style="gap: 4px; align-items: center;"):
                    _dl_csv(
                        "Download sweep CSV",
                        lambda r=result: export_sweep_to_csv(r, output_path=""),
                        f"sweep_{safe_s}_{safe_p}.csv",
                    )

        # ── Results card ────────────────────────────────────────────────
        with solara.Card("Results", style="margin-top: 0;"):
            with solara.Row(
                style="gap: 4px; justify-content: flex-end; margin-bottom: 4px;"
            ):
                _dl_png(
                    "Download sweep chart",
                    lambda p=png: p,
                    f"sweep_{safe_s}_{safe_p}.png",
                )
            solara.Image(png)

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
# Top-level
# ---------------------------------------------------------------------------


@solara.component
def BatchResultsPanel() -> Any:
    """Right-pane panel for batch results.

    Reads result directly from mc_run / sweep_run RunState singletons.
    Page-level state machine in page.py ensures this panel is only rendered
    when a result is ready — no spinner gate needed here.
    """
    mc = mc_run.value
    sw = sweep_run.value

    if mc.is_ready and mc.result is not None:
        _MCResultsView()
    elif sw.is_ready and sw.result is not None:
        _SweepResultsView()
    else:
        solara.Text("No batch results to display.")
