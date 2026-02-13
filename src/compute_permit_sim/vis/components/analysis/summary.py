"""Analysis Summary component — config + key metrics for a simulation run."""

import solara
import solara.lab

from compute_permit_sim.schemas import ScenarioConfig
from compute_permit_sim.vis.components import AutoConfigView


@solara.component
def AnalysisSummary(
    is_live: bool,
    config: ScenarioConfig | None,
    step_count: int,
    compliance_series: list,
    price_series: list,
):
    """Display key metrics and full run configuration."""
    if not config:
        return

    # Derive display values
    final_compliance = compliance_series[-1] if compliance_series else None
    final_price = price_series[-1] if price_series else None

    with solara.Card("Summary", style="margin-bottom: 12px;"):
        with solara.Row(style="gap: 24px; flex-wrap: wrap;"):
            _MetricChip("Steps", str(step_count))
            _MetricChip(
                "Compliance",
                f"{final_compliance:.0%}" if final_compliance is not None else "—",
            )
            _MetricChip(
                "Final Price",
                f"${final_price:.2f}" if final_price is not None else "—",
            )
            if config.seed is not None:
                _MetricChip("Seed", str(config.seed))

        solara.Markdown("---")
        with solara.Column(style="font-size: 0.95em;"):
            AutoConfigView(
                schema=ScenarioConfig,
                model=config,
                readonly=True,
                collapsible=True,
            )


@solara.component
def _MetricChip(label: str, value: str):
    """Small metric display chip."""
    solara.Markdown(f"**{label}:** {value}", style="white-space: nowrap;")
