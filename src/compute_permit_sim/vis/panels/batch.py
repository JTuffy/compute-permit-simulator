"""Batch analysis sidebar panel: Monte Carlo and Parameter Sweep configurators.

Two cards in the Batch sidebar tab:

1. **Monte Carlo** — pick a scenario, set N replications, fire run.
2. **Parameter Sweep** — pick a scenario, pick a sweepable parameter from the
   registry dropdown, set min/max/step range (prefilled from registry defaults),
   set replications per point, fire run.

Both run in background threads so the Solara event loop is not blocked.
Results are stored in module-level reactives so the right pane can display them.
Results are ephemeral — users download CSV to persist.
"""

from __future__ import annotations

import threading
from typing import Any

import solara

from compute_permit_sim.schemas.sweep_params import (
    SWEEPABLE_PARAMS,
    SweepParam,
    categories,
    generate_values,
    params_for_category,
)
from compute_permit_sim.vis.components.history import UnifiedHistoryList
from compute_permit_sim.vis.components.results import SidebarLabel
from compute_permit_sim.vis.state.run_state import RunState, mc_run, sweep_run

# Pre-built lookup map (module-level constant — registry never changes at runtime)
_PARAM_MAP: dict[str, SweepParam] = {p.path: p for p in SWEEPABLE_PARAMS}

# ---------------------------------------------------------------------------
# Internal status messages (error-only display in sidebar)
# ---------------------------------------------------------------------------
_mc_status = solara.reactive("")
_sweep_status = solara.reactive("")

# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------


def _load_scenario_by_name(name: str):
    """Return ScenarioConfig matching display ``name`` via session_history.scenario_name_map."""
    from compute_permit_sim.services.config_manager import load_scenario
    from compute_permit_sim.vis.state.history import session_history

    filename = session_history.scenario_name_map.value.get(name)
    if filename:
        return load_scenario(filename)
    return None


def _run_mc_background(scenario_name: str, n_runs: int) -> None:
    """Run Monte Carlo off the event loop thread and update mc_run reactive."""
    from compute_permit_sim.schemas.batch import MonteCarloResult
    from compute_permit_sim.services.monte_carlo import run_monte_carlo

    try:
        config = _load_scenario_by_name(scenario_name)

        if config is None:
            _mc_status.set(f"Scenario '{scenario_name}' not found.")
            mc_run.set(RunState[MonteCarloResult](phase="idle"))
            return

        _mc_status.set(f"Running {n_runs} seeds on {config.name}...")
        result = run_monte_carlo(config, n_runs=n_runs)

        # Store aggregate MC result in batch history for re-viewing from sidebar.
        # NOTE: raw_seeds are PerSeedResult (scalar summaries), not SimulationRun
        # objects — they cannot be added to run_history. The batch history list
        # (session_history.batch_results) is the correct mechanism for MC results.
        from compute_permit_sim.vis.state.history import (
            session_history,  # noqa: PLC0415
        )

        session_history.add_batch_result(result)

        # Set result + phase=ready atomically; page.py sees one transition.
        mc_run.set(RunState[MonteCarloResult](phase="ready", result=result))
        _mc_status.set(
            f"Done: {config.name} — avg compliance "
            f"{result.avg_compliance.mean:.1%} \u00b1 {result.avg_compliance.std:.1%} "
            f"({n_runs} seeds)"
        )
    except Exception as e:  # noqa: BLE001
        mc_run.set(RunState[MonteCarloResult](phase="idle"))
        _mc_status.set(f"Error: {e}")


def _run_sweep_background(
    scenario_name: str,
    param: SweepParam,
    values: list[float],
    n_runs: int,
) -> None:
    """Run parameter sweep off the event loop thread and update sweep_run reactive."""
    from compute_permit_sim.schemas.batch import SweepResult
    from compute_permit_sim.services.sweep import run_sweep

    try:
        config = _load_scenario_by_name(scenario_name)

        if config is None:
            _sweep_status.set(f"Scenario '{scenario_name}' not found.")
            sweep_run.set(RunState[SweepResult](phase="idle"))
            return

        n_pts = len(values)
        _sweep_status.set(f"Sweeping {param.label} — {n_pts} points × {n_runs} runs...")

        result = run_sweep(
            config,
            param_path=param.path,
            values=values,
            param_label=param.label,
            n_runs=n_runs,
        )

        tp = result.tipping_point()
        tp_str = f" | tipping point ≈ {tp:.3f}" if tp is not None else ""

        # Store sweep result in batch history for re-viewing from sidebar
        from compute_permit_sim.vis.state.history import (
            session_history,  # noqa: PLC0415
        )

        session_history.add_batch_result(result)

        # Set result + phase=ready atomically.
        sweep_run.set(RunState[SweepResult](phase="ready", result=result))
        _sweep_status.set(f"Done: {n_pts} points{tp_str}")
    except Exception as e:  # noqa: BLE001
        sweep_run.set(RunState[SweepResult](phase="idle"))
        _sweep_status.set(f"Error: {e}")


# ---------------------------------------------------------------------------
# Sub-components
# ---------------------------------------------------------------------------


@solara.component
def _MonteCarloCard(scenario_names: list[str]) -> Any:
    from compute_permit_sim.schemas.batch import MonteCarloResult

    selected, set_selected = solara.use_state(
        scenario_names[0] if scenario_names else ""
    )
    n_runs, set_n_runs = solara.use_state(20)
    is_running = mc_run.value.is_running
    status = _mc_status.value

    def on_run() -> None:
        mc_run.set(RunState[MonteCarloResult](phase="running"))
        # Also clear any stale sweep result so right pane shows MC spinner
        from compute_permit_sim.schemas.batch import SweepResult

        sweep_run.set(RunState[SweepResult](phase="idle"))
        _mc_status.set("Starting...")
        threading.Thread(
            target=_run_mc_background,
            args=(selected, n_runs),
            daemon=True,
        ).start()

    with solara.Card(title="Monte Carlo"):
        if not scenario_names:
            with solara.Column(classes=["sidebar-empty-text"]):
                solara.Text("No scenarios found.")
            return
        solara.Select(
            label="Scenario",
            values=scenario_names,
            value=selected,
            on_value=set_selected,
            dense=True,
        )
        solara.SliderInt(
            label=f"Replications: {n_runs}",
            value=n_runs,
            on_value=set_n_runs,
            min=5,
            max=200,
            step=5,
        )
        solara.Button(
            "Running..." if is_running else "Run Monte Carlo",
            on_click=on_run,
            color="primary",
            block=True,
            disabled=is_running or not selected,
            small=True,
        )
        if status and ("Error" in status or "not found" in status):
            with solara.Column(classes=["sidebar-error-text"]):
                solara.Text(status)


@solara.component
def _SweepCard(scenario_names: list[str]) -> Any:
    # Scenario
    selected_scenario, set_selected_scenario = solara.use_state(
        scenario_names[0] if scenario_names else ""
    )

    # Category + param selection
    all_categories = categories()
    selected_category, set_selected_category = solara.use_state(
        all_categories[0] if all_categories else ""
    )
    params_in_cat = params_for_category(selected_category)
    selected_param_path, set_selected_param_path = solara.use_state(
        params_in_cat[0].path if params_in_cat else ""
    )

    # Find the selected SweepParam to get defaults (use module-level map)
    current_param = _PARAM_MAP.get(selected_param_path)

    # Range inputs — prefilled from registry, editable
    min_val, set_min_val = solara.use_state(
        current_param.default_min if current_param else 0.0
    )
    max_val, set_max_val = solara.use_state(
        current_param.default_max if current_param else 1.0
    )
    step_val, set_step_val = solara.use_state(
        current_param.default_step if current_param else 0.1
    )
    n_runs, set_n_runs = solara.use_state(20)

    is_running = sweep_run.value.is_running
    status = _sweep_status.value

    # Compute preview
    preview_pts = 0
    preview_error = ""
    if current_param and step_val > 0 and min_val <= max_val:
        try:
            preview_pts = len(
                generate_values(current_param, min_val, max_val, step_val)
            )
        except Exception:
            preview_error = "Invalid range"

    def on_category_change(cat: str) -> None:
        set_selected_category(cat)
        new_params = params_for_category(cat)
        if new_params:
            p = new_params[0]
            set_selected_param_path(p.path)
            set_min_val(p.default_min)
            set_max_val(p.default_max)
            set_step_val(p.default_step)

    def on_param_change(path: str) -> None:
        set_selected_param_path(path)
        p = _PARAM_MAP.get(path)
        if p:
            set_min_val(p.default_min)
            set_max_val(p.default_max)
            set_step_val(p.default_step)

    def on_run() -> None:
        if not current_param:
            return
        try:
            vals = generate_values(current_param, min_val, max_val, step_val)
        except ValueError:
            _sweep_status.set("Invalid range or step — check min/max/step.")
            return
        from compute_permit_sim.schemas.batch import MonteCarloResult, SweepResult

        sweep_run.set(RunState[SweepResult](phase="running"))
        # Clear stale MC result so right pane shows sweep spinner
        mc_run.set(RunState[MonteCarloResult](phase="idle"))
        _sweep_status.set("Starting...")
        threading.Thread(
            target=_run_sweep_background,
            args=(selected_scenario, current_param, vals, n_runs),
            daemon=True,
        ).start()

    with solara.Card(title="Parameter Sweep"):
        if not scenario_names:
            with solara.Column(classes=["sidebar-empty-text"]):
                solara.Text("No scenarios found.")
            return

        solara.Select(
            label="Scenario",
            values=scenario_names,
            value=selected_scenario,
            on_value=set_selected_scenario,
            dense=True,
        )
        solara.Select(
            label="Category",
            values=all_categories,
            value=selected_category,
            on_value=on_category_change,
            dense=True,
        )
        param_labels = [p.label for p in params_in_cat]
        param_label_to_path = {p.label: p.path for p in params_in_cat}
        current_label = (
            current_param.label
            if current_param
            else (param_labels[0] if param_labels else "")
        )

        def on_param_label_change(label: str) -> None:
            path = param_label_to_path.get(label, "")
            on_param_change(path)

        solara.Select(
            label="Parameter",
            values=param_labels,
            value=current_label,
            on_value=on_param_label_change,
            dense=True,
        )

        # Description hint
        if current_param:
            with solara.Column(classes=["sidebar-hint-text"]):
                solara.Text(current_param.description)

        with solara.Row(style="gap: 4px;"):
            solara.InputFloat(
                label=f"Min ({current_param.unit if current_param else ''})",
                value=min_val,
                on_value=set_min_val,
            )
            solara.InputFloat(
                label=f"Max ({current_param.unit if current_param else ''})",
                value=max_val,
                on_value=set_max_val,
            )
            solara.InputFloat(
                label="Step",
                value=step_val,
                on_value=set_step_val,
            )

        solara.SliderInt(
            label=f"Runs per point: {n_runs}",
            value=n_runs,
            on_value=set_n_runs,
            min=5,
            max=200,
            step=5,
        )

        # Preview count / error
        if preview_error:
            with solara.Column(classes=["sidebar-error-text"]):
                solara.Text(preview_error)
        elif preview_pts > 0:
            total = preview_pts * n_runs
            with solara.Column(classes=["sidebar-hint-text"]):
                solara.Text(
                    f"{total:,} total simulations ({preview_pts} pts × {n_runs})"
                )

        solara.Button(
            "Running..." if is_running else "Run Sweep",
            on_click=on_run,
            color="primary",
            block=True,
            disabled=is_running
            or not selected_scenario
            or not current_param
            or preview_pts == 0,
            small=True,
        )
        if status and (
            "Error" in status or "not found" in status or "Invalid" in status
        ):
            with solara.Column(classes=["sidebar-error-text"]):
                solara.Text(status)


# ---------------------------------------------------------------------------
# Public panel
# ---------------------------------------------------------------------------


@solara.component
def BatchPanel() -> Any:
    """Sidebar panel with Monte Carlo and Parameter Sweep configurators."""
    from compute_permit_sim.vis.state.history import session_history  # noqa: PLC0415

    # Use the same name map as LoadScenarioDialog for consistency
    scenario_names = sorted(session_history.scenario_name_map.value.keys())

    with solara.Column(classes=["sidebar-compact"]):
        SidebarLabel("**BATCH ANALYSIS**")
        _MonteCarloCard(scenario_names=scenario_names)
        _SweepCard(scenario_names=scenario_names)

        # ── History — batch results + individual runs in one stream ────────
        solara.Markdown("---")
        with solara.Column(classes=["sidebar-history-section"]):
            SidebarLabel("**HISTORY**")
            UnifiedHistoryList()
