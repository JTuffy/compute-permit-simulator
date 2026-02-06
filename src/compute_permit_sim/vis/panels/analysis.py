import pandas as pd
import solara

from compute_permit_sim.services.metrics import (
    calculate_compliance,
    calculate_wealth_stats,
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
    _ = active_sim.state.value.step_count

    # Step index state for historical timeline (hoisted to ensure consistent hook calls)
    run_id = run.id if run else "live"
    step_idx, set_step_idx = solara.use_state(0, key=run_id)

    # --- Memoized time series (only recompute when run changes, not on slider move) ---
    def compute_time_series():
        if is_live:
            return (
                active_sim.state.value.compliance_history,
                active_sim.state.value.price_history,
                (
                    active_sim.state.value.wealth_history_compliant,
                    active_sim.state.value.wealth_history_non_compliant,
                ),
            )
        elif run and run.steps:
            compliance = []
            prices = []
            w_comp = []
            w_non = []
            for s in run.steps:
                # Compliance & Price
                compliance.append(calculate_compliance(s.agents))
                prices.append(s.market.price)

                # Wealth
                w_c, w_nc = calculate_wealth_stats(s.agents)
                w_comp.append(w_c)
                w_non.append(w_nc)

            return compliance, prices, (w_comp, w_non)
        return [], [], ([], [])

    compliance_series, price_series, wealth_series = solara.use_memo(
        compute_time_series,
        dependencies=[run_id, active_sim.state.value if is_live else 0],
    )

    # --- Extract step-specific data ---
    if is_live:
        step_count = active_sim.state.value.step_count
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

    # --- Derived values for Summary ---
    # (Checking compliance_series again inside component, or pass directly)
    # Passed directly to AnalysisSummary

    # --- Render Unified Layout ---
    with solara.Column(classes=["analysis-panel"]):
        # SECTION 1: Key Metrics & Config
        AnalysisSummary(
            is_live=is_live,
            config=config,
            step_count=step_count,
            compliance_series=compliance_series,
            price_series=price_series,
        )

        # SECTION 2: Time Series Graphs
        RunGraphs(compliance_series, price_series, wealth_series)

        # SECTION 3-6: Step Inspector & Analysis
        StepInspector(
            is_live=is_live,
            run=run,
            step_idx=step_idx,
            set_step_idx=set_step_idx,
            market_price=market_price,
            market_supply=market_supply,
            agents_df=agents_df,
            config=config,
        )
