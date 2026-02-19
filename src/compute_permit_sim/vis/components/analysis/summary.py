"""Analysis Summary component — config + key metrics for a simulation run."""

import solara
import solara.lab

from compute_permit_sim.schemas import RunMetrics, ScenarioConfig
from compute_permit_sim.vis.components import AutoConfigView


@solara.component
def AnalysisSummary(
    is_live: bool,
    config: ScenarioConfig | None,
    step_count: int,
    metrics: RunMetrics | None,  # Pass full metrics object
):
    """Display key metrics and full run configuration."""
    if not config:
        return

    with solara.Card("Summary", style="margin-bottom: 12px;"):
        with solara.Row(style="gap: 24px; flex-wrap: wrap;"):
            _MetricChip("Steps", str(step_count))

            # Dynamically render metrics from global source of truth
            if metrics:
                for field_name, field_info in RunMetrics.model_fields.items():
                    val = getattr(metrics, field_name)
                    # Use description or title as label
                    label = (
                        field_info.description.split("(")[0].strip()
                        if field_info.description
                        else field_name.replace("_", " ").title()
                    )

                    # Simple heuristic formatting (shared logic with export.py ideally)
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

        solara.Markdown("---")
        with solara.Details("Full Configuration"):
            with solara.Column(style="font-size: 0.95em;"):
                AutoConfigView(
                    schema=ScenarioConfig,
                    model=config,
                    readonly=True,
                    render_mode="tabs",
                )


@solara.component
def _MetricChip(label: str, value: str):
    """Small metric display chip."""
    solara.Markdown(f"**{label}:** {value}", style="white-space: nowrap;")
