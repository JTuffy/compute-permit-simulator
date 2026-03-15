"""Parameter sweep runner for the Compute Permit Simulator.

Runs a scenario across a grid of values for one parameter and
returns per-point Monte Carlo results, enabling tipping-point and
sensitivity analysis for Section 4.4 of the paper.

Usage:
    from compute_permit_sim.services.sweep import run_sweep
    result = run_sweep(
        config,
        param_path="audit.base_prob",
        values=[0.01, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30],
        n_runs=50,
    )
    for p in result.points:
        print(p.param_value, p.result.avg_compliance.mean)
"""

from __future__ import annotations

from compute_permit_sim.schemas.batch import GridSweepResult, SweepPoint, SweepResult
from compute_permit_sim.schemas.config import ScenarioConfig
from compute_permit_sim.services.monte_carlo import run_monte_carlo


def _set_nested(d: dict, path: str, value: object) -> dict:
    """Return a new dict with the dot-path key set to value (shallow-copies each level)."""
    parts = path.split(".", 1)
    key = parts[0]
    d = dict(d)  # shallow copy at this level
    if len(parts) == 1:
        d[key] = value
    else:
        d[key] = _set_nested(dict(d.get(key, {})), parts[1], value)
    return d


def override_config(
    config: ScenarioConfig, param_path: str, value: object
) -> ScenarioConfig:
    """Return a new ScenarioConfig with one field overridden via dot-path notation.

    Examples:
        override_config(cfg, "audit.base_prob", 0.15)
        override_config(cfg, "collateral_amount", 50.0)
        override_config(cfg, "market.fixed_price", 10.0)

    Args:
        config: Original (frozen) ScenarioConfig.
        param_path: Dot-separated path to the field, e.g. "audit.base_prob".
        value: New value to assign.

    Returns:
        New ScenarioConfig with the field updated.
    """
    d = config.model_dump()
    updated = _set_nested(d, param_path, value)
    return ScenarioConfig.model_validate(updated)


def run_sweep(
    base_config: ScenarioConfig,
    param_path: str,
    values: list[float],
    param_label: str | None = None,
    n_runs: int = 50,
    seeds: list[int] | None = None,
) -> SweepResult:
    """Run a 1D parameter sweep over a scenario.

    Each value in ``values`` produces one Monte Carlo run (N replications).
    All other parameters are held fixed at their ``base_config`` values.

    Args:
        base_config: Base scenario configuration to sweep from.
        param_path: Dot-separated config path to vary, e.g. "audit.base_prob".
        values: List of values to sweep over. Must be valid for the target field.
        param_label: Optional human-readable label for the parameter (for exports).
                     Defaults to the param_path itself.
        n_runs: Replications per sweep point. Ignored if ``seeds`` is provided.
        seeds: Explicit seeds to use for every sweep point. If None, sequential
               integers 0..n_runs-1 are used consistently across all points.

    Returns:
        SweepResult with one MonteCarloResult per value.
    """
    label = param_label or param_path
    run_seeds = seeds if seeds is not None else list(range(n_runs))

    points: list[SweepPoint] = []
    for v in values:
        config_v = override_config(base_config, param_path, v)
        mc_result = run_monte_carlo(config_v, seeds=run_seeds)
        points.append(SweepPoint(param_value=v, result=mc_result))

    return SweepResult(
        scenario_name=base_config.name,
        param_path=param_path,
        param_label=label,
        config=base_config,
        points=points,
    )


def run_sweep_from_registry(
    base_config,
    param_path: str,
    min_val: float | None = None,
    max_val: float | None = None,
    step: float | None = None,
    n_runs: int = 50,
    seeds: list[int] | None = None,
):
    """Run a sweep using the sweepable parameter registry for range defaults.

    Looks up ``param_path`` in ``SWEEPABLE_PARAMS`` to fill in default
    min/max/step values.  Any supplied arguments override those defaults.

    Args:
        base_config: Base scenario configuration to sweep from.
        param_path: Dot-path registered in ``SWEEPABLE_PARAMS``.
        min_val: Sweep start (inclusive). Uses registry default if None.
        max_val: Sweep end (inclusive). Uses registry default if None.
        step: Interval between values. Uses registry default if None.
        n_runs: MC replications per sweep point.
        seeds: Explicit seeds (overrides n_runs if provided).

    Returns:
        SweepResult for the generated value grid.

    Raises:
        KeyError: If param_path is not in the registry.
    """
    from compute_permit_sim.schemas.sweep_params import generate_values, get_param

    param = get_param(param_path)
    values = generate_values(param, min_val=min_val, max_val=max_val, step=step)
    return run_sweep(
        base_config,
        param_path=param.path,
        values=values,
        param_label=param.label,
        n_runs=n_runs,
        seeds=seeds,
    )


def run_grid_sweep(
    base_config: ScenarioConfig,
    param_x_path: str,
    param_y_path: str,
    x_values: list[float],
    y_values: list[float],
    param_x_label: str | None = None,
    param_y_label: str | None = None,
    n_runs: int = 20,
    seeds: list[int] | None = None,
) -> GridSweepResult:
    """Run a 2D joint-sensitivity sweep over two parameters.

    Each (x, y) cell is evaluated with ``n_runs`` Monte Carlo replications.
    Results are stored as ``grid[y_idx][x_idx] = mean_compliance``.

    All seeds are shared across all cells so that parameter variation, not
    noise, drives differences between cells.

    Args:
        base_config: Base scenario configuration.
        param_x_path: Dot-path for the x-axis parameter, e.g. ``"audit.base_prob"``.
        param_y_path: Dot-path for the y-axis parameter, e.g. ``"collateral_amount"``.
        x_values: Ordered x-axis values.
        y_values: Ordered y-axis values.
        param_x_label: Human-readable x-axis label; defaults to ``param_x_path``.
        param_y_label: Human-readable y-axis label; defaults to ``param_y_path``.
        n_runs: MC replications per cell. Ignored if ``seeds`` is provided.
        seeds: Explicit seeds; overrides ``n_runs`` if given.

    Returns:
        :class:`~compute_permit_sim.schemas.batch.GridSweepResult` with the 2D
        compliance grid and axis metadata.
    """
    label_x = param_x_label or param_x_path
    label_y = param_y_label or param_y_path
    run_seeds = seeds if seeds is not None else list(range(n_runs))

    # grid[y_idx][x_idx] = mean compliance
    grid: list[list[float]] = []
    for y in y_values:
        row: list[float] = []
        for x in x_values:
            cfg = override_config(base_config, param_x_path, x)
            cfg = override_config(cfg, param_y_path, y)
            mc = run_monte_carlo(cfg, seeds=run_seeds)
            row.append(mc.avg_compliance.mean)
        grid.append(row)

    return GridSweepResult(
        scenario_name=base_config.name,
        param_x_path=param_x_path,
        param_x_label=label_x,
        param_y_path=param_y_path,
        param_y_label=label_y,
        config=base_config,
        x_values=list(x_values),
        y_values=list(y_values),
        grid=grid,
        n_runs=len(run_seeds),
    )


def run_grid_sweep_from_registry(
    base_config: ScenarioConfig,
    param_x_path: str,
    param_y_path: str,
    x_min: float | None = None,
    x_max: float | None = None,
    x_step: float | None = None,
    y_min: float | None = None,
    y_max: float | None = None,
    y_step: float | None = None,
    n_runs: int = 20,
    seeds: list[int] | None = None,
) -> GridSweepResult:
    """Run a 2D grid sweep using registry defaults for both axis ranges.

    Looks up each path in ``SWEEPABLE_PARAMS`` to fill in default
    min/max/step values.  Any supplied arguments override those defaults.

    Args:
        base_config: Base scenario configuration.
        param_x_path: Dot-path registered in ``SWEEPABLE_PARAMS`` for x-axis.
        param_y_path: Dot-path registered in ``SWEEPABLE_PARAMS`` for y-axis.
        x_min/x_max/x_step: Override registry defaults for x-axis.
        y_min/y_max/y_step: Override registry defaults for y-axis.
        n_runs: MC replications per cell.
        seeds: Explicit seeds (overrides n_runs if provided).

    Returns:
        :class:`~compute_permit_sim.schemas.batch.GridSweepResult`.

    Raises:
        KeyError: If either path is not in the registry.
    """
    from compute_permit_sim.schemas.sweep_params import generate_values, get_param

    px = get_param(param_x_path)
    py = get_param(param_y_path)
    x_values = generate_values(px, min_val=x_min, max_val=x_max, step=x_step)
    y_values = generate_values(py, min_val=y_min, max_val=y_max, step=y_step)
    return run_grid_sweep(
        base_config,
        param_x_path=px.path,
        param_y_path=py.path,
        x_values=x_values,
        y_values=y_values,
        param_x_label=px.label,
        param_y_label=py.label,
        n_runs=n_runs,
        seeds=seeds,
    )
