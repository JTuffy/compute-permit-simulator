"""Unified analysis panel — displays a SimulationRun result.

Reads from ``session_history.selected_run`` (historical selection) or
``basic_run.value.result`` (most recent run). The page-level state machine
in ``vis/page.py`` ensures this panel is never rendered while a run is active,
so no spinner gate is needed here.
"""

from __future__ import annotations

import logging

import solara

from compute_permit_sim.schemas import SimulationRun
from compute_permit_sim.services.metrics import calculate_compliance
from compute_permit_sim.vis.components.analysis.graphs import ResultsContent
from compute_permit_sim.vis.components.analysis.inspector import AgentDetailsTable
from compute_permit_sim.vis.components.analysis.summary import AnalysisSummary
from compute_permit_sim.vis.state.history import session_history
from compute_permit_sim.vis.state.run_state import basic_run

logger = logging.getLogger(__name__)


@solara.component
def AnalysisPanel():
    """Display a complete SimulationRun result.

    Data source priority:
    1. session_history.selected_run  (user clicked a historical run)
    2. basic_run.value.result        (most recent run just completed)
    """
    # Resolve the run — hooks must be registered before any early return
    run: SimulationRun | None = (
        session_history.selected_run.value or basic_run.value.result
    )
    run_id = run.id if run else "none"

    step_idx, set_step_idx = solara.use_state(0, key=run_id)
    view_mode, set_view_mode = solara.use_state("Aggregate", key=f"vm-{run_id}")

    def compute_series() -> tuple[list[float], list[float], list[int]]:
        if run is None:
            return [], [], []
        compliance = [calculate_compliance(s.agents) for s in run.steps]
        prices = [s.market.price for s in run.steps]
        caught = [sum(1 for a in s.agents if a.was_caught) for s in run.steps]
        return compliance, prices, caught

    compliance_series, price_series, caught_series = solara.use_memo(
        compute_series, dependencies=[run_id]
    )

    # No run available (page.py should show EmptyState instead, but guard anyway)
    if run is None:
        return

    step_count = len(run.steps)
    can_step = step_count > 0

    with solara.Column(classes=["analysis-panel"]):
        AnalysisSummary(
            is_live=False,
            config=run.config,
            step_count=step_count,
            metrics=run.metrics,
            run=run,
        )

        ResultsContent(
            view_mode=view_mode,
            set_view_mode=set_view_mode,
            can_step=can_step,
            step_idx=step_idx,
            set_step_idx=set_step_idx,
            compliance_series=compliance_series,
            caught_series=caught_series,
            price_series=price_series,
            steps=run.steps,
            live_agents_df=None,
            is_live=False,
        )

        AgentDetailsTable(
            steps=run.steps,
            step_idx=step_idx,
            live_agents_df=None,
            is_live=False,
        )
