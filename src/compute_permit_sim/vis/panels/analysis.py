from __future__ import annotations

import logging

import solara

from compute_permit_sim.schemas import RunMetrics, ScenarioConfig
from compute_permit_sim.services.metrics import (
    calculate_compliance,
)
from compute_permit_sim.vis.components.analysis.graphs import ResultsContent
from compute_permit_sim.vis.components.analysis.inspector import AgentDetailsTable
from compute_permit_sim.vis.components.analysis.summary import AnalysisSummary
from compute_permit_sim.vis.state.active import active_sim
from compute_permit_sim.vis.state.config import ui_config
from compute_permit_sim.vis.state.history import session_history

logger = logging.getLogger(__name__)


@solara.component
def AnalysisPanel():
    """Unified analysis panel with a mode toggle.

    AnalysisPanel is responsible for data orchestration only:
    - Resolves run vs live context
    - Memoizes time series
    - Holds view_mode and step_idx state
    - Passes scalar props (no DataFrames) to ResultsContent and AgentDetailsTable,
      which compute agents_df internally for reliable Solara reactivity.
    """
    # --- Unified Data Access ---
    run = session_history.selected_run.value
    is_live = run is None

    step_count_live = active_sim.state.value.step_count
    is_playing = active_sim.state.value.is_playing

    run_id = run.id if run else "live"
    step_idx, set_step_idx = solara.use_state(0, key=run_id)
    view_mode, set_view_mode = solara.use_state("Aggregate", key=f"vm-{run_id}")

    can_step = not is_live and run is not None and len(run.steps) > 0

    # --- Memoized time series ---
    def compute_time_series():
        if is_live:
            return (
                active_sim.state.value.compliance_history,
                active_sim.state.value.price_history,
                [],
            )
        elif run and run.steps:
            compliance = []
            prices = []
            caught = []
            for s in run.steps:
                compliance.append(calculate_compliance(s.agents))
                prices.append(s.market.price)
                caught.append(
                    sum(1 for a in s.agents if getattr(a, "was_caught", False))
                )
            return compliance, prices, caught
        return [], [], []

    compliance_series, price_series, caught_series = solara.use_memo(
        compute_time_series,
        dependencies=[run_id, step_count_live if is_live else 0],
    )

    # --- Config + Metrics ---
    config: ScenarioConfig | None = None
    if is_live:
        step_count = step_count_live
        config = ui_config.to_scenario_config()
    else:
        step_count = len(run.steps) if run else 0
        config = run.config if run else None

    if is_live:
        metrics = None
        if step_count_live > 0:
            try:
                state = active_sim.state.value
                final_compliance = (
                    state.compliance_history[-1] if state.compliance_history else 0.0
                )
                final_price = state.price_history[-1] if state.price_history else 0.0
                avg_compliance = (
                    sum(state.compliance_history) / len(state.compliance_history)
                    if state.compliance_history
                    else 0.0
                )
                metrics = RunMetrics(
                    final_compliance=final_compliance,
                    final_price=final_price,
                    deterrence_success_rate=avg_compliance,
                )
            except Exception as exc:
                logger.debug("Could not build live RunMetrics: %s", exc)
    else:
        metrics = run.metrics if run else None

    # --- Live agent data (live mode only) ---
    live_agents_df = active_sim.state.value.agents_df if is_live else None
    steps_for_results = run.steps if (not is_live and run) else None

    # --- Render ---
    with solara.Column(classes=["analysis-panel"]):
        # SECTION 1: Key Metrics & Config
        AnalysisSummary(
            is_live=is_live,
            config=config,
            step_count=step_count,
            metrics=metrics,
            run=run,
        )

        # SECTION 2: Results — toggle + slider + charts in one unified card
        # agents_df is computed inside ResultsContent from steps + step_idx
        # so that scalar integer props drive reactivity (not DataFrame props)
        ResultsContent(
            view_mode=view_mode,
            set_view_mode=set_view_mode,
            can_step=can_step,
            step_idx=step_idx,
            set_step_idx=set_step_idx,
            compliance_series=compliance_series,
            caught_series=caught_series,
            price_series=price_series,
            steps=steps_for_results,
            live_agents_df=live_agents_df,
            is_playing=is_playing,
            is_live=is_live,
        )

        # SECTION 3: Agent Details Table
        # Also uses steps + step_idx (scalars) for reactivity
        AgentDetailsTable(
            steps=steps_for_results,
            step_idx=step_idx,
            live_agents_df=live_agents_df,
            is_live=is_live,
        )
