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

from compute_permit_sim.schemas.batch import SweepPoint, SweepResult
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
