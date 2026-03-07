"""Entry point for the Compute Permit Simulator.

Usage:
    make run                         # single run, all scenarios
    make mc                          # Monte Carlo (50 runs per scenario)
    make sweep                       # π₀ × K sensitivity sweep on Lawless
    make paper-results               # MC + sweep, outputs LaTeX snippet

    uv run main.py --runs 1          # single run (default)
    uv run main.py --monte-carlo 50  # 50-run MC on all scenarios
    uv run main.py --sweep scenario_1_minimal.json audit.base_prob 0.01,0.05,0.10,0.20,0.30
"""

from __future__ import annotations

import argparse
import logging
import os
import time

from compute_permit_sim.schemas import (
    MarketSnapshot,
    RunMetrics,
    ScenarioConfig,
    SimulationRun,
    StepResult,
)
from compute_permit_sim.services.mesa_model import ComputePermitModel
from compute_permit_sim.services.metrics import calculate_compliance
from compute_permit_sim.vis.export import (
    export_monte_carlo_to_csv,
    export_monte_carlo_to_latex,
    export_run_to_csv,
    export_run_to_excel,
    export_sweep_to_csv,
)

logger = logging.getLogger("compute_permit_sim.cli")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# =============================================================================
# Single-run logic (unchanged from original)
# =============================================================================


def run_scenario(config: ScenarioConfig) -> list[str] | None:
    """Run a single scenario and export results.

    Args:
        config: Validated scenario configuration.

    Returns:
        List of generated file paths, or None if no steps were produced.
    """
    logger.info(f"--- Running {config.name}: {config.description} ---")
    model = ComputePermitModel(config=config)
    steps = []

    for step_num in range(1, config.steps + 1):
        model.step()

        agents = model.get_agent_snapshots()
        step_res = StepResult(
            step=step_num,
            market=MarketSnapshot(
                price=model.market.current_price,
                supply=model.market.max_supply,
            ),
            agents=agents,
            audit=[],
        )
        steps.append(step_res)

    if not steps:
        logger.info(f"Results for {config.name}: No data collected.\n")
        return None

    final_compliance = calculate_compliance(steps[-1].agents)
    run_timestamp = time.strftime("%Y%m%d_%H%M%S")

    run = SimulationRun(
        id=f"run_{run_timestamp}",
        config=config,
        steps=steps,
        metrics=RunMetrics(
            final_compliance=final_compliance,
            final_price=model.market.current_price,
            deterrence_success_rate=final_compliance,
        ),
    )

    safe_name = (
        "".join(c for c in config.name if c.isalnum() or c in (" ", "_"))
        .rstrip()
        .replace(" ", "_")
        .lower()
    )

    os.makedirs("outputs", exist_ok=True)
    csv_filename = f"outputs/{safe_name}_{run_timestamp}.csv"
    excel_filename = f"outputs/{safe_name}_{run_timestamp}.xlsx"

    generated_files = []
    try:
        export_run_to_csv(run, csv_filename)
        generated_files.append(csv_filename)
        logger.info(f"Saved CSV results to {csv_filename}")
    except Exception as e:
        logger.error(f"Failed to save CSV: {e}")

    try:
        export_run_to_excel(run, excel_filename)
        generated_files.append(excel_filename)
        logger.info(f"Saved Excel results to {excel_filename}")
    except Exception as e:
        logger.error(f"Failed to save Excel: {e}")

    logger.info(f"Results for {config.name}:")
    logger.info(f"  Final Compliance Rate: {final_compliance:.2%}")
    logger.info(f"  Final Market Price:    {model.market.current_price:.2f}\n")
    return generated_files


# =============================================================================
# Monte Carlo
# =============================================================================


def run_all_monte_carlo(n_runs: int) -> None:
    """Run Monte Carlo on all canonical scenarios and export CSV + LaTeX."""
    from compute_permit_sim.services.config_manager import list_scenarios, load_scenario
    from compute_permit_sim.services.monte_carlo import run_monte_carlo

    scenarios = list_scenarios()
    if not scenarios:
        logger.info("No scenarios found.")
        return

    logger.info(f"Monte Carlo: {n_runs} runs × {len(scenarios)} scenarios")
    results = []
    for filename in sorted(scenarios):
        config = load_scenario(filename)
        logger.info(f"  Running {config.name} ...")
        result = run_monte_carlo(config, n_runs=n_runs)
        results.append(result)
        logger.info(
            f"    avg_compliance={result.avg_compliance.mean:.1%} "
            f"(±{result.avg_compliance.std:.1%})  "
            f"avg_payoff={result.avg_net_payoff.mean:.2f}M$ "
            f"(±{result.avg_net_payoff.std:.2f})"
        )

    os.makedirs("outputs", exist_ok=True)
    csv_path = export_monte_carlo_to_csv(results, "outputs/monte_carlo_summary.csv")
    assert isinstance(csv_path, str)
    logger.info(f"Saved MC summary CSV \u2192 {csv_path}")

    latex = export_monte_carlo_to_latex(results)
    latex_path = "outputs/monte_carlo_table.tex"
    with open(latex_path, "w", encoding="utf-8") as f:
        f.write(latex)
    logger.info(f"Saved LaTeX table \u2192 {latex_path}")


# =============================================================================
# Sweep
# =============================================================================


def run_single_sweep(
    scenario_file: str,
    param_path: str,
    values: list[float],
    n_runs: int,
) -> None:
    """Run a 1D parameter sweep on one scenario and export CSV."""
    from compute_permit_sim.services.config_manager import load_scenario
    from compute_permit_sim.services.sweep import run_sweep

    config = load_scenario(scenario_file)
    logger.info(
        f"Sweep: {config.name} \u00d7 {param_path} "
        f"({len(values)} points \u00d7 {n_runs} runs each)"
    )
    result = run_sweep(config, param_path, values, n_runs=n_runs)

    os.makedirs("outputs", exist_ok=True)
    csv_path = export_sweep_to_csv(result)
    if not isinstance(csv_path, str):
        raise TypeError(f"Expected file path string, got {type(csv_path)}")
    logger.info(f"Saved sweep CSV \u2192 {csv_path}")
    for pt in result.points:
        logger.info(
            f"  {param_path}={pt.param_value:.4f}  "
            f"compliance={pt.result.avg_compliance.mean:.1%}"
        )


# =============================================================================
# Entrypoint
# =============================================================================


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute Permit Simulator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--monte-carlo",
        metavar="N",
        type=int,
        help="Run Monte Carlo with N replications per scenario.",
    )
    mode.add_argument(
        "--sweep",
        nargs=5,
        metavar=("SCENARIO_FILE", "PARAM_PATH", "MIN", "MAX", "INTERVAL"),
        help=(
            "Run a parameter sweep. SCENARIO_FILE: path relative to scenarios/, "
            "PARAM_PATH: dot-path e.g. audit.base_prob, "
            "MIN/MAX/INTERVAL: sweep range e.g. 0.01 0.30 0.05"
        ),
    )
    mode.add_argument(
        "--sweep-file",
        metavar="SWEEP_FILE",
        type=str,
        help="Run a sweep from a JSON file in scenarios/sweeps/ (e.g. sweep_pi0_lawless.json).",
    )

    parser.add_argument(
        "--runs-per-point",
        type=int,
        default=50,
        help="MC replications per sweep point (used with --sweep). Default: 50.",
    )

    return parser.parse_args()


def main() -> None:
    """Load and run all scenarios, or run Monte Carlo / sweep."""
    args = _parse_args()

    if args.monte_carlo:
        run_all_monte_carlo(n_runs=args.monte_carlo)
        return

    if args.sweep_file:
        from compute_permit_sim.schemas.sweep_params import generate_values, get_param
        from compute_permit_sim.services.config_manager import load_sweep

        sweep_cfg = load_sweep(args.sweep_file)
        # Generate values from min/max/interval using the registry for rounding
        try:
            param = get_param(sweep_cfg.param_path)
            values = generate_values(
                param, sweep_cfg.min_val, sweep_cfg.max_val, sweep_cfg.interval
            )
        except KeyError:
            # Param not in registry — generate values manually with consistent rounding

            n_pts = (
                round((sweep_cfg.max_val - sweep_cfg.min_val) / sweep_cfg.interval) + 1
            )
            values = [
                round(sweep_cfg.min_val + i * sweep_cfg.interval, 8)
                for i in range(n_pts)
                if sweep_cfg.min_val + i * sweep_cfg.interval
                <= sweep_cfg.max_val + 1e-9
            ]
        run_single_sweep(
            sweep_cfg.scenario_file,
            sweep_cfg.param_path,
            values,
            n_runs=len(sweep_cfg.seeds) if sweep_cfg.seeds else sweep_cfg.n_runs,
        )
        return

    if args.sweep:
        scenario_file, param_path, min_str, max_str, interval_str = args.sweep
        min_val, max_val, interval = float(min_str), float(max_str), float(interval_str)
        from compute_permit_sim.schemas.sweep_params import generate_values, get_param

        try:
            param = get_param(param_path)
            values = generate_values(param, min_val, max_val, interval)
        except KeyError:
            n_pts = round((max_val - min_val) / interval) + 1
            values = [
                round(min_val + i * interval, 8)
                for i in range(n_pts)
                if min_val + i * interval <= max_val + 1e-9
            ]
        run_single_sweep(scenario_file, param_path, values, n_runs=args.runs_per_point)
        return

    # Default: single run of all scenarios
    from compute_permit_sim.services.config_manager import list_scenarios, load_scenario

    scenarios = list_scenarios()
    if not scenarios:
        logger.info("No scenarios found in scenarios/ directory.")
        return

    logger.info(f"Found {len(scenarios)} scenarios.")
    all_generated_files: list[str] = []
    for filename in scenarios:
        try:
            config = load_scenario(filename)
            files = run_scenario(config)
            if files:
                all_generated_files.extend(files)
        except Exception as e:
            logger.error(f"Failed to run {filename}: {e}")

    if all_generated_files:
        import zipfile

        bundle_timestamp = time.strftime("%Y%m%d_%H%M%S")
        bundle_name = f"outputs/simulation_bundle_{bundle_timestamp}.zip"
        try:
            with zipfile.ZipFile(bundle_name, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file in all_generated_files:
                    zipf.write(file, os.path.basename(file))
            print(f"Bundled {len(all_generated_files)} files → {bundle_name}")
        except Exception as e:
            print(f"Failed to create zip bundle: {e}")


if __name__ == "__main__":
    main()
