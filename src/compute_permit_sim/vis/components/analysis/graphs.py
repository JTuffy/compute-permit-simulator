"""Results content — mode-aware sim-level results panel.

Owns the view-mode toggle, step slider, and all chart rendering in a single
card. This keeps the toggle/slider/charts visually unified and ensures slider
reactivity: step_idx is a scalar integer prop, so Solara always detects
changes cleanly (unlike DataFrame props, which are compared by ambiguous ==).

Mode logic:
- "Aggregate" (default): time series + 4 full-run aggregate charts
- "Step-by-Step": slider drives step index; 4 step-level charts shown
- Live simulation: toggle hidden, forced into aggregate mode
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Literal

import pandas as pd
import solara

from compute_permit_sim.vis.components.charts import (
    AuditSourcePlot,
    AuditTargetingPlot,
    ComplianceDistributionPlot,
    RiskScatterPlot,
)
from compute_permit_sim.vis.components.charts.expandable import ExpandableChart
from compute_permit_sim.vis.plotting import plot_time_series

if TYPE_CHECKING:
    pass

_VIEW_OPTIONS = ["Aggregate", "Step-by-Step"]


@solara.component
def ResultsContent(
    view_mode: str,
    set_view_mode: Callable[[str], None],
    can_step: bool,
    step_idx: int,
    set_step_idx: Callable[[int], None],
    compliance_series: list | pd.Series,
    caught_series: list | pd.Series,
    price_series: list | pd.Series,
    steps: list | None = None,
    live_agents_df: pd.DataFrame | None = None,
    is_playing: bool = False,
    is_live: bool = False,
) -> None:
    """Unified results card: toggle, slider, and charts in one section.

    ``step_idx`` is an integer so Solara's prop-change detection is reliable.
    ``agents_df`` is computed here from ``steps[step_idx]`` rather than
    being passed in as a prop, which avoids DataFrame equality comparison issues.
    """
    # Resolve effective mode
    effective_mode: Literal["aggregate", "step"] = (
        "step" if (can_step and view_mode == "Step-by-Step") else "aggregate"
    )

    # Compute agents_df locally — step_idx is the reactive scalar, not agents_df
    agents_df: pd.DataFrame | None = None
    market_price: float = 0.0
    market_supply: float = 0.0

    if is_live:
        agents_df = live_agents_df
    elif effective_mode == "step" and steps and len(steps) > 0:
        idx = max(0, min(step_idx, len(steps) - 1))
        step = steps[idx]
        market_price = step.market.price
        market_supply = step.market.supply
        agents_df = pd.DataFrame([a.model_dump() for a in step.agents])

    with solara.Card("Results"):
        # --- Live progress banner ---
        if is_playing:
            with solara.Row(
                style="align-items: center; gap: 12px; margin-bottom: 8px;"
            ):
                solara.v.ProgressCircular(
                    indeterminate=True, color="primary", size=20, width=3
                )
                solara.Text("Simulating…", style="color: #888; font-style: italic;")

        # --- Toggle + Slider (historical with steps only) ---
        if can_step:
            with solara.Row(
                style="align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 8px;"
            ):
                solara.Markdown("**View:**", style="margin: 0; white-space: nowrap;")
                solara.ToggleButtonsSingle(
                    value=view_mode,
                    on_value=set_view_mode,
                    values=_VIEW_OPTIONS,
                )

            if effective_mode == "step" and steps:
                solara.SliderInt(
                    label="Step",
                    value=step_idx,
                    on_value=set_step_idx,
                    min=0,
                    max=len(steps) - 1,
                    thumb_label="always",
                )
                solara.Markdown(
                    f"**Step {step_idx + 1}** of {len(steps)} — "
                    f"Clearing Price: ${market_price:.2f} | "
                    f"Permits: {market_supply:.0f}"
                )

            solara.Markdown("---")

        # --- Aggregate mode: time series + full-run charts ---
        if effective_mode == "aggregate":
            with solara.Columns([1, 1, 1]):
                with solara.Column():
                    if compliance_series:
                        fig = plot_time_series(
                            compliance_series,
                            "Compliance Rate",
                            "green",
                            title="Compliance Rate",
                            ylabel="Rate (0–1)",
                            ylim=(-0.05, 1.05),
                        )
                        ExpandableChart(fig)
                    else:
                        solara.Markdown("*No compliance data yet*")

                with solara.Column():
                    if price_series:
                        fig = plot_time_series(
                            price_series,
                            "Market Price",
                            "blue",
                            title="Permit Price",
                            ylabel="Price ($)",
                        )
                        ExpandableChart(fig)
                    else:
                        solara.Markdown("*No price data yet*")

                with solara.Column():
                    if caught_series:
                        fig = plot_time_series(
                            caught_series,
                            "Labs Caught",
                            "orange",
                            title="Labs Caught per Step",
                            ylabel="Count",
                        )
                        ExpandableChart(fig)
                    else:
                        solara.Markdown("*No enforcement data yet*")

            if steps:
                with solara.Columns([1, 1, 1]):
                    with solara.Column():
                        RiskScatterPlot(mode="aggregate", steps=steps)
                    with solara.Column():
                        AuditTargetingPlot(mode="aggregate", steps=steps)
                    with solara.Column():
                        ComplianceDistributionPlot(mode="aggregate", steps=steps)

                with solara.Columns([1, 1, 1]):
                    with solara.Column():
                        AuditSourcePlot(mode="aggregate", steps=steps)
                    with solara.Column():
                        pass  # reserved
                    with solara.Column():
                        pass  # reserved

        # --- Step mode: slider-driven charts ---
        else:
            with solara.Columns([1, 1, 1]):
                with solara.Column():
                    RiskScatterPlot(mode="step", agents_df=agents_df)
                with solara.Column():
                    AuditTargetingPlot(mode="step", agents_df=agents_df)
                with solara.Column():
                    ComplianceDistributionPlot(mode="step", agents_df=agents_df)

            with solara.Columns([1, 1, 1]):
                with solara.Column():
                    AuditSourcePlot(mode="step", agents_df=agents_df)
                with solara.Column():
                    pass  # reserved
                with solara.Column():
                    pass  # reserved
