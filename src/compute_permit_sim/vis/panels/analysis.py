import pandas as pd
import solara

from compute_permit_sim.schemas import ScenarioConfig
from compute_permit_sim.services.metrics import (
    calculate_compliance,
)
from compute_permit_sim.vis.components.analysis.graphs import RunGraphs
from compute_permit_sim.vis.components.analysis.inspector import StepInspector
from compute_permit_sim.vis.components.analysis.summary import AnalysisSummary
from compute_permit_sim.vis.state.active import active_sim
from compute_permit_sim.vis.state.config import ui_config
from compute_permit_sim.vis.state.history import session_history


@solara.component
def AnalysisPanel():
    """Unified analysis panel combining metrics, timeline, graphs, and agent table.

    Renders consistently regardless of live vs historical mode by using a
    unified data access pattern at the top.
    """
    # --- Unified Data Access ---
    run = session_history.selected_run.value
    is_live = run is None

    # Force dependency on step count for live updates
    step_count_live = active_sim.state.value.step_count
    is_playing = active_sim.state.value.is_playing

    # Step index state for historical timeline (hoisted to ensure consistent hook calls)
    run_id = run.id if run else "live"
    step_idx, set_step_idx = solara.use_state(0, key=run_id)

    # --- Memoized time series (only recompute when run changes, not on slider move) ---
    # Use scalar dependencies only: step_count (int) or run_id (str).
    # Passing the full SimulationState object caused memo to always miss because
    # model_copy() creates a new object identity on every step.
    def compute_time_series():
        if is_live:
            return (
                active_sim.state.value.compliance_history,
                active_sim.state.value.price_history,
                [],  # caught_series not tracked live — empty for now
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
        # Live: re-run only when step_count changes (not on every state mutation).
        # Historical: re-run only when the selected run changes.
        dependencies=[run_id, step_count_live if is_live else 0],
    )

    # --- Extract step-specific data ---
    config: ScenarioConfig | None = None
    agents_df: pd.DataFrame | None = None
    if is_live:
        step_count = step_count_live
        agents_df = active_sim.state.value.agents_df
        market_price = (
            active_sim.state.value.model.market.current_price
            if active_sim.state.value.model
            else 0
        )
        market_supply = (
            active_sim.state.value.model.market.max_supply
            if active_sim.state.value.model
            else 0
        )

        # Determine config for display
        config = ui_config.to_scenario_config()

    else:
        step_count = len(run.steps) if run else 0

        # Get step-specific data based on slider (not memoized - changes with slider)
        if run and len(run.steps) > 0:
            idx = max(0, min(step_idx, len(run.steps) - 1))
            step = run.steps[idx]
            market_price = step.market.price
            market_supply = step.market.supply
            agents_df = pd.DataFrame([a.model_dump() for a in step.agents])
        else:
            idx = 0
            market_price = 0
            market_supply = 0
            agents_df = None

        config = run.config if run else None

    # --- Derive metrics ---
    if is_live:
        metrics = None
        if step_count_live > 0:
            try:
                from compute_permit_sim.schemas.data import RunMetrics

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
            except Exception:
                pass
    else:
        metrics = run.metrics if run else None

    # --- Render Unified Layout ---
    with solara.Column(classes=["analysis-panel"]):
        # SECTION 1: Key Metrics & Config
        AnalysisSummary(
            is_live=is_live,
            config=config,
            step_count=step_count,
            metrics=metrics,
        )

        # SECTION 2: Run Summary (time series + historical breakdowns)
        steps_for_graphs = run.steps if (not is_live and run) else None
        RunGraphs(
            compliance_series,
            caught_series,
            price_series,
            steps_for_graphs,
            is_playing=is_playing,
        )

        # SECTION 3-6: Step Inspector & Analysis
        StepInspector(
            is_live=is_live,
            run=run,
            step_idx=step_idx,
            set_step_idx=set_step_idx,
            market_price=market_price,
            market_supply=market_supply,
            agents_df=agents_df,
        )
