"""One-command reproduction of every figure and table in the paper.

Entry point: ``run_paper_pipeline()`` (CLI: ``uv run main.py --paper``).

Outputs (written to ``outputs/paper/`` by default):
    figures/   — every .png referenced by the manuscript, named identically
    tables/    — tab:compliance-summary and tab:audit-burden as .tex
    data/      — per-step trajectory CSVs used by the pgfplots appendix figures

The mapping between committed config files and paper figures is explicit in
``SWEEP_FIGURES`` and ``GRID_FIGURES`` below — one JSON per figure. Protocol
constants (seed counts) are defined here as the single source of truth and
must match the paper's experimental-protocol subsection (Section 3.3):
    Monte Carlo n=100, 1D sweeps n=30, 2D grids n=20 per cell.
"""

from __future__ import annotations

import json
import logging
import os

from compute_permit_sim.schemas.batch import MonteCarloResult
from compute_permit_sim.services.config_manager import SCENARIO_DIR, load_scenario
from compute_permit_sim.services.monte_carlo import run_monte_carlo
from compute_permit_sim.services.sweep import run_grid_sweep, run_sweep

logger = logging.getLogger(__name__)

# --- Experimental protocol (must match paper Section 3.3) -------------------
MC_RUNS = 100  # Monte Carlo replications per scenario
SWEEP_RUNS = 30  # replications per 1D sweep point
GRID_RUNS = 20  # replications per 2D grid cell
BASELINE_RUNS = (
    30  # replications per single-lever sensitivity point (matches 1D protocol)
)

# --- Scenario set ------------------------------------------------------------
MC_SCENARIOS = [
    "basic/scenario_1_minimal.json",
    "basic/scenario_2_strict.json",
    "basic/scenario_3_smart.json",
]

# Per-step trajectory CSVs for the pgfplots figures in Appendix D.
TRAJECTORY_CSVS = {
    "basic/scenario_4_feedback_compliance.json": "compliance_ratchet.csv",
    "basic/scenario_5_enforcement_cycles.json": "compliance_oscillation.csv",
}

# --- Figure registries: config file -> paper figure filename -----------------
SWEEP_FIGURES = {
    "sweep_permit_cap_minimal.json": "minimal_permit_cap.png",
    "sweep_pi0_minimal.json": "minimal_audit_prob.png",
    "sweep_price_strict.json": "strict_fixed_price.png",
    "sweep_valuation_strict.json": "strict_valuation_max.png",
    "sweep_price_smart.json": "smart_fixed_price.png",
    "sweep_reputation_dynamic.json": "dynamic_reputation_escalation.png",
    "sweep_penalty_dynamic.json": "dynamic_penalty.png",
    # Runs but is not (yet) a manuscript figure — see collateral discussion:
    "sweep_collateral_minimal.json": "minimal_collateral.png",
}

GRID_FIGURES = {
    "grid_minimal_q_pi0.json": "heatmap_minimal.png",
    "grid_strict_price_vmax.json": "heatmap_strict.png",
    "grid_smart_price_pi0.json": "heatmap_smart.png",
    "grid_dynamic_pi0_eps.json": "heatmap_dynamic.png",
}

# Single-lever sensitivity from the constructed baseline (Section 4 headline).
# All sweep the same baseline scenario; one tornado figure + one table summarise
# the relative impact of each lever. Order here is the legend/plot input order;
# the figure and table re-sort by impact (compliance span).
BASELINE_SCENARIO = "basic/baseline.json"
BASELINE_SENSITIVITY_SWEEPS = [
    "sweep_baseline_price.json",
    "sweep_baseline_pi0.json",
    "sweep_baseline_collateral.json",
    "sweep_baseline_penalty.json",
    "sweep_baseline_detection.json",
]


def _sweep_dir() -> str:
    return os.path.join(SCENARIO_DIR, "sweeps")


def _grid_dir() -> str:
    return os.path.join(SCENARIO_DIR, "grids")


def _sweep_values(min_val: float, max_val: float, interval: float) -> list[float]:
    n_pts = round((max_val - min_val) / interval) + 1
    return [
        round(min_val + i * interval, 8)
        for i in range(n_pts)
        if min_val + i * interval <= max_val + 1e-9
    ]


def _linspace(min_val: float, max_val: float, n: int) -> list[float]:
    if n == 1:
        return [min_val]
    step = (max_val - min_val) / (n - 1)
    return [round(min_val + i * step, 8) for i in range(n)]


def run_paper_monte_carlo(
    out_dir: str, n_runs: int = MC_RUNS
) -> list[MonteCarloResult]:
    """Monte Carlo for the headline scenarios: violin figure + both tables."""
    from compute_permit_sim.vis.export import (
        export_compliance_summary_to_latex,
        export_workload_to_latex,
    )
    from compute_permit_sim.vis.plotting import plot_compliance_violin, save_figure

    results: list[MonteCarloResult] = []
    for scenario_file in MC_SCENARIOS:
        config = load_scenario(scenario_file)
        logger.info(f"[paper] MC {config.name} (n={n_runs})")
        results.append(run_monte_carlo(config, n_runs=n_runs, store_raw=True))

    fig = plot_compliance_violin(results)
    save_figure(
        fig, os.path.join(out_dir, "figures", "fig_compliance_distribution.png")
    )

    tables_dir = os.path.join(out_dir, "tables")
    for name, tex in (
        ("compliance_summary.tex", export_compliance_summary_to_latex(results)),
        ("audit_burden.tex", export_workload_to_latex(results)),
    ):
        with open(os.path.join(tables_dir, name), "w", encoding="utf-8") as f:
            f.write(tex + "\n")
    return results


def run_paper_trajectories(out_dir: str, n_runs: int = MC_RUNS) -> None:
    """Per-step compliance trajectory CSVs for the Appendix D pgfplots figures.

    CSV schema matches the manuscript's ``data/*.csv``: step, mean, lower,
    upper — where lower/upper are mean -/+ 1 SD across seeds, clipped to [0, 1].
    """
    for scenario_file, csv_name in TRAJECTORY_CSVS.items():
        config = load_scenario(scenario_file)
        logger.info(f"[paper] trajectory {config.name} (n={n_runs})")
        mc = run_monte_carlo(config, n_runs=n_runs)
        path = os.path.join(out_dir, "data", csv_name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("step,mean,lower,upper\n")
            for i, stats in enumerate(mc.step_compliance, start=1):
                lower = max(0.0, stats.mean - stats.std)
                upper = min(1.0, stats.mean + stats.std)
                f.write(f"{i},{stats.mean:.6f},{lower:.6f},{upper:.6f}\n")


def run_paper_sweeps(out_dir: str, n_runs: int | None = None) -> None:
    """All 1D sweep figures, one committed JSON per figure."""
    from compute_permit_sim.vis.plotting import plot_sweep_curve, save_figure

    for sweep_file, fig_name in SWEEP_FIGURES.items():
        with open(os.path.join(_sweep_dir(), sweep_file), encoding="utf-8") as f:
            cfg = json.load(f)
        config = load_scenario(cfg["scenario_file"])
        values = _sweep_values(cfg["min_val"], cfg["max_val"], cfg["interval"])
        runs = n_runs if n_runs is not None else cfg.get("n_runs", SWEEP_RUNS)
        logger.info(f"[paper] sweep {sweep_file} ({len(values)} pts, n={runs})")
        result = run_sweep(
            config,
            cfg["param_path"],
            values,
            param_label=cfg.get("param_label"),
            n_runs=runs,
        )
        fig = plot_sweep_curve(result)
        save_figure(fig, os.path.join(out_dir, "figures", fig_name))


def run_paper_grids(out_dir: str, n_runs: int | None = None) -> None:
    """All 2D heatmap figures, one committed JSON per figure."""
    from compute_permit_sim.vis.plotting import plot_sweep_heatmap, save_figure

    for grid_file, fig_name in GRID_FIGURES.items():
        with open(os.path.join(_grid_dir(), grid_file), encoding="utf-8") as f:
            cfg = json.load(f)
        config = load_scenario(cfg["scenario_file"])
        x, y = cfg["x"], cfg["y"]
        x_values = _linspace(x["min_val"], x["max_val"], x["n_values"])
        y_values = _linspace(y["min_val"], y["max_val"], y["n_values"])
        runs = n_runs if n_runs is not None else cfg.get("n_runs", GRID_RUNS)
        logger.info(
            f"[paper] grid {grid_file} "
            f"({len(x_values)}x{len(y_values)} cells, n={runs})"
        )
        result = run_grid_sweep(
            config,
            param_x_path=x["param_path"],
            param_y_path=y["param_path"],
            x_values=x_values,
            y_values=y_values,
            param_x_label=x.get("param_label"),
            param_y_label=y.get("param_label"),
            n_runs=runs,
        )
        highlight = tuple(cfg["highlight"]) if cfg.get("highlight") else None
        fig = plot_sweep_heatmap(
            result.grid,
            result.x_values,
            result.y_values,
            x_param_label=result.param_x_label,
            y_param_label=result.param_y_label,
            highlight=highlight,
        )
        save_figure(fig, os.path.join(out_dir, "figures", fig_name))


def run_paper_baseline_sensitivity(out_dir: str, n_runs: int | None = None) -> None:
    """Single-lever sensitivity from the constructed baseline (Section 4 headline).

    Sweeps each enforcement lever one at a time from ``BASELINE_SCENARIO`` and
    produces two artifacts: the tornado figure ``fig_lever_sensitivity.png`` and
    the table ``lever_sensitivity.tex``. The baseline compliance reference is
    measured once via Monte Carlo at the unswept configuration.
    """
    from compute_permit_sim.services.monte_carlo import run_monte_carlo
    from compute_permit_sim.vis.export import export_lever_sensitivity_to_latex
    from compute_permit_sim.vis.plotting import plot_lever_tornado, save_figure

    runs = n_runs if n_runs is not None else BASELINE_RUNS
    base_config = load_scenario(BASELINE_SCENARIO)
    baseline_mc = run_monte_carlo(base_config, n_runs=runs)
    baseline_compliance = baseline_mc.avg_compliance.mean
    logger.info(
        f"[paper] baseline compliance {baseline_compliance:.3f} "
        f"(SD {baseline_mc.avg_compliance.std:.3f}, n={runs})"
    )

    sweeps = []
    for sweep_file in BASELINE_SENSITIVITY_SWEEPS:
        with open(os.path.join(_sweep_dir(), sweep_file), encoding="utf-8") as f:
            cfg = json.load(f)
        values = _sweep_values(cfg["min_val"], cfg["max_val"], cfg["interval"])
        logger.info(
            f"[paper] baseline sweep {sweep_file} ({len(values)} pts, n={runs})"
        )
        sweeps.append(
            run_sweep(
                base_config,
                cfg["param_path"],
                values,
                param_label=cfg.get("param_label"),
                n_runs=runs,
            )
        )

    fig = plot_lever_tornado(sweeps, baseline_compliance)
    save_figure(fig, os.path.join(out_dir, "figures", "fig_lever_sensitivity.png"))

    tex = export_lever_sensitivity_to_latex(sweeps, baseline_compliance)
    with open(
        os.path.join(out_dir, "tables", "lever_sensitivity.tex"), "w", encoding="utf-8"
    ) as f:
        f.write(tex + "\n")


def _write_provenance(out_dir: str, protocol_overridden: bool) -> None:
    """Stamp the artifacts with the commit, date, and protocol used.

    The manuscript's Appendix C reproduction hash should be taken from this
    file rather than typed by hand.
    """
    import datetime
    import subprocess

    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        commit, dirty = "unknown", True

    lines = [
        f"commit: {commit}{' (dirty — do not publish)' if dirty else ''}",
        f"generated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
        f"protocol: mc={MC_RUNS} sweeps={SWEEP_RUNS} grids={GRID_RUNS}"
        + (" (OVERRIDDEN — smoke run, do not publish)" if protocol_overridden else ""),
    ]
    with open(os.path.join(out_dir, "PROVENANCE.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    logger.info(f"[paper] provenance: {lines[0]}")


def run_paper_pipeline(
    out_dir: str = "outputs/paper",
    mc_runs: int | None = None,
    sweep_runs: int | None = None,
    grid_runs: int | None = None,
) -> None:
    """Regenerate every paper figure and table.

    Args:
        out_dir: Output root; figures/, tables/, data/ are created inside.
        mc_runs / sweep_runs / grid_runs: Optional overrides of the paper
            protocol — intended for smoke tests only. Published artifacts
            must use the defaults.
    """
    for sub in ("figures", "tables", "data"):
        os.makedirs(os.path.join(out_dir, sub), exist_ok=True)

    overridden = any(v is not None for v in (mc_runs, sweep_runs, grid_runs))
    _write_provenance(out_dir, protocol_overridden=overridden)
    run_paper_monte_carlo(out_dir, n_runs=mc_runs or MC_RUNS)
    run_paper_trajectories(out_dir, n_runs=mc_runs or MC_RUNS)
    run_paper_baseline_sensitivity(out_dir, n_runs=sweep_runs)
    run_paper_sweeps(out_dir, n_runs=sweep_runs)
    run_paper_grids(out_dir, n_runs=grid_runs)
    logger.info(f"[paper] complete — artifacts in {out_dir}/")
