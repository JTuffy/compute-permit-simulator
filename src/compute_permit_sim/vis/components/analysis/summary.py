"""Analysis Summary component — config + key metrics for a simulation run."""

from __future__ import annotations

import solara
import solara.lab

from compute_permit_sim.schemas import RunMetrics, ScenarioConfig
from compute_permit_sim.vis.components.dialogs import RunConfigDialog


@solara.component
def AnalysisSummary(
    is_live: bool,
    config: ScenarioConfig | None,
    step_count: int,
    metrics: RunMetrics | None,
    run=None,  # SimulationRun | None — passed for the export button
):
    """Display key metrics and full run configuration."""
    if not config:
        return

    with solara.Card("Summary", style="margin-bottom: 12px;"):
        with solara.Row(
            style="align-items: center; justify-content: space-between; flex-wrap: wrap;"
        ):
            # --- Metric chips row ---
            with solara.Row(style="gap: 24px; flex-wrap: wrap; flex: 1;"):
                _MetricChip("Steps", str(step_count))

                # Collateral — key lever, always visible when non-zero
                if config.collateral_amount > 0:
                    _MetricChip("Collateral", f"${config.collateral_amount:.0f}M")

                # Dynamically render metrics from RunMetrics schema
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
                        _MetricChip(label, value_str)
                else:
                    _MetricChip("Status", "In Progress..." if is_live else "No Metrics")

                if config.seed is not None:
                    _MetricChip("Seed", str(config.seed))

            # --- Action buttons ---
            with solara.Row(style="gap: 4px; align-items: center;"):
                # ⓘ Config params dialog — same component as run history
                run_title = (
                    f"Run: {run.sim_id or run.id}" if run else "Active Configuration"
                )
                RunConfigDialog(
                    config=config,
                    title=run_title,
                    metrics=metrics if (run is not None) else None,
                )

                # Export buttons (historical runs only)
                if run is not None:
                    from compute_permit_sim.vis.export import (
                        export_run_to_csv,
                        export_run_to_excel,
                    )

                    fname = run.sim_id or run.id
                    with solara.Tooltip("Export to Excel"):
                        with solara.FileDownload(
                            filename=f"{fname}.xlsx",
                            data=lambda: export_run_to_excel(run, output_path=""),
                            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        ):
                            solara.Button(
                                icon_name="mdi-file-excel-outline",
                                icon=True,
                                small=True,
                            )
                    with solara.Tooltip("Export to CSV"):
                        with solara.FileDownload(
                            filename=f"{fname}.csv",
                            data=lambda: export_run_to_csv(run, output_path=""),
                            mime_type="text/csv",
                        ):
                            solara.Button(
                                icon_name="mdi-file-delimited-outline",
                                icon=True,
                                small=True,
                            )


@solara.component
def _MetricChip(label: str, value: str):
    """Small metric display chip."""
    solara.Markdown(f"**{label}:** {value}", style="white-space: nowrap;")
