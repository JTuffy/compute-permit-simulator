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
from compute_permit_sim.vis.state.run_state import RunState, grid_run, mc_run, sweep_run

# Pre-built lookup map (module-level constant — registry never changes at runtime)
_PARAM_MAP: dict[str, SweepParam] = {p.path: p for p in SWEEPABLE_PARAMS}

# ---------------------------------------------------------------------------
# Internal status messages (error-only display in sidebar)
# ---------------------------------------------------------------------------
_mc_status = solara.reactive("")
_sweep_status = solara.reactive("")
_grid_status = solara.reactive("")

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


def _run_grid_background(
    scenario_name: str,
    param_x: SweepParam,
    param_y: SweepParam,
    x_values: list[float],
    y_values: list[float],
    n_runs: int,
) -> None:
    """Run 2D grid sweep off the event loop thread and update grid_run reactive."""
    from compute_permit_sim.schemas.batch import GridSweepResult
    from compute_permit_sim.services.sweep import run_grid_sweep

    try:
        config = _load_scenario_by_name(scenario_name)

        if config is None:
            _grid_status.set(f"Scenario '{scenario_name}' not found.")
            grid_run.set(RunState[GridSweepResult](phase="idle"))
            return

        n_cells = len(x_values) * len(y_values)
        _grid_status.set(
            f"Grid {len(x_values)}×{len(y_values)} = {n_cells} cells × {n_runs} runs..."
        )

        result = run_grid_sweep(
            config,
            param_x_path=param_x.path,
            param_y_path=param_y.path,
            x_values=x_values,
            y_values=y_values,
            param_x_label=param_x.label,
            param_y_label=param_y.label,
            n_runs=n_runs,
        )

        from compute_permit_sim.vis.state.history import (
            session_history,  # noqa: PLC0415
        )

        session_history.add_batch_result(result)
        grid_run.set(RunState[GridSweepResult](phase="ready", result=result))
        _grid_status.set(
            f"Done: {len(x_values)}×{len(y_values)} grid — "
            f"compliance {result.compliance_min:.1%}–{result.compliance_max:.1%}"
        )
    except Exception as e:  # noqa: BLE001
        from compute_permit_sim.schemas.batch import GridSweepResult

        grid_run.set(RunState[GridSweepResult](phase="idle"))
        _grid_status.set(f"Error: {e}")


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
def _GridSweepCard(scenario_names: list[str]) -> Any:
    """Sidebar card for configuring and launching a 2D grid sweep."""
    selected_scenario, set_selected_scenario = solara.use_state(
        scenario_names[0] if scenario_names else ""
    )

    all_categories = categories()

    # --- X-axis param ---
    cat_x, set_cat_x = solara.use_state(all_categories[0] if all_categories else "")
    params_x = params_for_category(cat_x)
    path_x, set_path_x = solara.use_state(params_x[0].path if params_x else "")
    param_x = _PARAM_MAP.get(path_x)
    min_x, set_min_x = solara.use_state(param_x.default_min if param_x else 0.0)
    max_x, set_max_x = solara.use_state(param_x.default_max if param_x else 1.0)
    step_x, set_step_x = solara.use_state(param_x.default_step if param_x else 0.1)

    # --- Y-axis param ---
    cat_y, set_cat_y = solara.use_state(all_categories[0] if all_categories else "")
    params_y = params_for_category(cat_y)
    path_y, set_path_y = solara.use_state(params_y[0].path if params_y else "")
    param_y = _PARAM_MAP.get(path_y)
    min_y, set_min_y = solara.use_state(param_y.default_min if param_y else 0.0)
    max_y, set_max_y = solara.use_state(param_y.default_max if param_y else 1.0)
    step_y, set_step_y = solara.use_state(param_y.default_step if param_y else 0.1)

    n_runs, set_n_runs = solara.use_state(20)

    is_running = grid_run.value.is_running
    status = _grid_status.value

    # Compute preview — both axes must be valid
    n_pts_x, n_pts_y = 0, 0
    preview_error = ""
    if param_x and step_x > 0 and min_x <= max_x:
        try:
            n_pts_x = len(generate_values(param_x, min_x, max_x, step_x))
        except Exception:
            preview_error = "Invalid X range"
    if param_y and step_y > 0 and min_y <= max_y:
        try:
            n_pts_y = len(generate_values(param_y, min_y, max_y, step_y))
        except Exception:
            preview_error = "Invalid Y range"

    def _on_cat_x(cat: str) -> None:
        set_cat_x(cat)
        ps = params_for_category(cat)
        if ps:
            set_path_x(ps[0].path)
            set_min_x(ps[0].default_min)
            set_max_x(ps[0].default_max)
            set_step_x(ps[0].default_step)

    def _on_path_x(label: str) -> None:
        path = {p.label: p.path for p in params_for_category(cat_x)}.get(label, "")
        set_path_x(path)
        p = _PARAM_MAP.get(path)
        if p:
            set_min_x(p.default_min)
            set_max_x(p.default_max)
            set_step_x(p.default_step)

    def _on_cat_y(cat: str) -> None:
        set_cat_y(cat)
        ps = params_for_category(cat)
        if ps:
            set_path_y(ps[0].path)
            set_min_y(ps[0].default_min)
            set_max_y(ps[0].default_max)
            set_step_y(ps[0].default_step)

    def _on_path_y(label: str) -> None:
        path = {p.label: p.path for p in params_for_category(cat_y)}.get(label, "")
        set_path_y(path)
        p = _PARAM_MAP.get(path)
        if p:
            set_min_y(p.default_min)
            set_max_y(p.default_max)
            set_step_y(p.default_step)

    def on_run() -> None:
        if not param_x or not param_y:
            return
        try:
            x_vals = generate_values(param_x, min_x, max_x, step_x)
            y_vals = generate_values(param_y, min_y, max_y, step_y)
        except ValueError:
            _grid_status.set("Invalid range — check min/max/step for both axes.")
            return
        from compute_permit_sim.schemas.batch import (  # noqa: PLC0415
            GridSweepResult,
            MonteCarloResult,
            SweepResult,
        )

        grid_run.set(RunState[GridSweepResult](phase="running"))
        mc_run.set(RunState[MonteCarloResult](phase="idle"))
        sweep_run.set(RunState[SweepResult](phase="idle"))
        _grid_status.set("Starting...")
        threading.Thread(
            target=_run_grid_background,
            args=(selected_scenario, param_x, param_y, x_vals, y_vals, n_runs),
            daemon=True,
        ).start()

    with solara.Card(title="Grid Sweep"):
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

        # ── X-axis ──────────────────────────────────────────────────────────
        with solara.Column(classes=["sidebar-hint-text"]):
            solara.Text("X-axis parameter")
        with solara.Row(style="gap: 4px;"):
            solara.Select(
                label="Category",
                values=all_categories,
                value=cat_x,
                on_value=_on_cat_x,
                dense=True,
            )
            labels_x = [p.label for p in params_for_category(cat_x)]
            solara.Select(
                label="Parameter",
                values=labels_x,
                value=param_x.label if param_x else (labels_x[0] if labels_x else ""),
                on_value=_on_path_x,
                dense=True,
            )
        with solara.Row(style="gap: 4px;"):
            unit_x = param_x.unit if param_x else ""
            solara.InputFloat(label=f"Min ({unit_x})", value=min_x, on_value=set_min_x)
            solara.InputFloat(label=f"Max ({unit_x})", value=max_x, on_value=set_max_x)
            solara.InputFloat(label="Step", value=step_x, on_value=set_step_x)

        # ── Y-axis ──────────────────────────────────────────────────────────
        with solara.Column(classes=["sidebar-hint-text"]):
            solara.Text("Y-axis parameter")
        with solara.Row(style="gap: 4px;"):
            solara.Select(
                label="Category",
                values=all_categories,
                value=cat_y,
                on_value=_on_cat_y,
                dense=True,
            )
            labels_y = [p.label for p in params_for_category(cat_y)]
            solara.Select(
                label="Parameter",
                values=labels_y,
                value=param_y.label if param_y else (labels_y[0] if labels_y else ""),
                on_value=_on_path_y,
                dense=True,
            )
        with solara.Row(style="gap: 4px;"):
            unit_y = param_y.unit if param_y else ""
            solara.InputFloat(label=f"Min ({unit_y})", value=min_y, on_value=set_min_y)
            solara.InputFloat(label=f"Max ({unit_y})", value=max_y, on_value=set_max_y)
            solara.InputFloat(label="Step", value=step_y, on_value=set_step_y)

        # ── Replications + simulation count preview ──────────────────────────
        solara.SliderInt(
            label=f"Runs per cell: {n_runs}",
            value=n_runs,
            on_value=set_n_runs,
            min=5,
            max=100,
            step=5,
        )
        if preview_error:
            with solara.Column(classes=["sidebar-error-text"]):
                solara.Text(preview_error)
        elif n_pts_x > 0 and n_pts_y > 0:
            total = n_pts_x * n_pts_y * n_runs
            with solara.Column(classes=["sidebar-hint-text"]):
                solara.Text(
                    f"{n_pts_x}\u00d7{n_pts_y} = {n_pts_x * n_pts_y} cells"
                    f" \u00d7 {n_runs} = {total:,} total simulations"
                )

        solara.Button(
            "Running..." if is_running else "Run Grid Sweep",
            on_click=on_run,
            color="primary",
            block=True,
            disabled=is_running
            or not selected_scenario
            or not param_x
            or not param_y
            or n_pts_x == 0
            or n_pts_y == 0,
            small=True,
        )
        if status and (
            "Error" in status or "not found" in status or "Invalid" in status
        ):
            with solara.Column(classes=["sidebar-error-text"]):
                solara.Text(status)


@solara.component
def BatchPanel() -> Any:
    """Sidebar panel with Monte Carlo, Parameter Sweep, and Grid Sweep configurators."""
    from compute_permit_sim.vis.state.history import session_history  # noqa: PLC0415

    # Use the same name map as LoadScenarioDialog for consistency
    scenario_names = sorted(session_history.scenario_name_map.value.keys())

    with solara.Column(classes=["sidebar-compact"]):
        SidebarLabel("**BATCH ANALYSIS**")
        _MonteCarloCard(scenario_names=scenario_names)
        _SweepCard(scenario_names=scenario_names)
        _GridSweepCard(scenario_names=scenario_names)

        # ── History — batch results + individual runs in one stream ────────
        solara.Markdown("---")
        with solara.Column(classes=["sidebar-history-section"]):
            SidebarLabel("**HISTORY**")
            UnifiedHistoryList()
