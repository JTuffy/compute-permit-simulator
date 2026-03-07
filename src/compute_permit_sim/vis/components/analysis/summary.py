"""Analysis Summary component — config + key metrics for a simulation run."""

from __future__ import annotations

import solara

from compute_permit_sim.schemas import RunMetrics, ScenarioConfig
from compute_permit_sim.vis.components.dialogs import RunConfigDialog
from compute_permit_sim.vis.components.results import (
    DownloadCSV,
    DownloadExcel,
    DownloadJSON,
    MetricChip,
    ResultsActions,
)


@solara.component
def AnalysisSummary(
    is_live: bool,
    config: ScenarioConfig | None,
    step_count: int,
    metrics: RunMetrics | None,
    run=None,  # SimulationRun | None — passed for export + rerun actions
):
    """Display key metrics and full run configuration."""
    if not config:
        return

    with solara.Card("Summary", style="margin-bottom: 12px;"):
        with solara.Row(
            style="align-items: center; justify-content: space-between; flex-wrap: wrap;"
        ):
            # --- Metric chips row (left) ---
            with solara.Row(style="gap: 24px; flex-wrap: wrap; flex: 1;"):
                MetricChip("Steps", str(step_count))

                if config.collateral_amount > 0:
                    MetricChip("Collateral", f"${config.collateral_amount:.0f}M")

                if metrics:
                    for field_name, field_info in RunMetrics.model_fields.items():
                        val = getattr(metrics, field_name)
                        label = (
                            field_info.description.split("(")[0].strip()
                            if field_info.description
                            else field_name.replace("_", " ").title()
                        )
                        if "rate" in field_name or "compliance" in field_name:
                            value_str = f"{val:.1%}"
                        elif "price" in field_name or "cost" in field_name:
                            value_str = f"${val:.2f}"
                        else:
                            value_str = f"{val:.2f}"
                        MetricChip(label, value_str)
                else:
                    MetricChip("Status", "In Progress..." if is_live else "No Metrics")

                if config.seed is not None:
                    MetricChip("Seed", str(config.seed))

            # --- Action buttons (right, bordered subsection) ---
            with ResultsActions():
                run_title = (
                    f"Run: {run.sim_id or run.id}" if run else "Active Configuration"
                )
                RunConfigDialog(
                    config=config,
                    title=run_title,
                    metrics=metrics if (run is not None) else None,
                )

                if run is not None:
                    from compute_permit_sim.vis.export import (
                        export_run_to_csv,
                        export_run_to_excel,
                    )

                    fname = run.sim_id or run.id

                    DownloadExcel(
                        "Export to Excel",
                        lambda: export_run_to_excel(run, output_path=""),
                        f"{fname}.xlsx",
                    )
                    DownloadCSV(
                        "Export to CSV",
                        lambda: export_run_to_csv(run, output_path=""),
                        f"{fname}.csv",
                    )
                    DownloadJSON(
                        "Export full run JSON (for reproducibility)",
                        lambda: run.model_dump_json(indent=2).encode("utf-8"),
                        f"{fname}.json",
                    )
