"""Generate CSV data for the two dynamic scenario plots in documents/figures/.

Outputs:
    documents/figures/compliance_ratchet.csv     (scenario_5_reputation_ratchet)
    documents/figures/compliance_oscillation.csv (scenario_6_enforcement_cycles)

Each CSV has columns: step, mean, lower (mean-std), upper (mean+std)

Usage:
    uv run scripts/generate_figure_data.py [--runs N]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from compute_permit_sim.services.config_manager import load_scenario
from compute_permit_sim.services.monte_carlo import run_monte_carlo


def write_csv(path: Path, step_compliance: list) -> None:
    """Write step,mean,lower,upper CSV from a list of MetricStats."""
    with path.open("w") as f:
        f.write("step,mean,lower,upper\n")
        for i, stats in enumerate(step_compliance):
            mean = stats.mean
            std = stats.std
            lower = max(0.0, mean - std)
            upper = min(1.0, mean + std)
            f.write(f"{i + 1},{mean:.4f},{lower:.4f},{upper:.4f}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs",
        type=int,
        default=200,
        help="Monte Carlo runs per scenario (default: 200)",
    )
    args = parser.parse_args()

    out_dir = Path(__file__).parent.parent / "documents" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    scenarios = [
        (
            "basic/scenario_5_reputation_ratchet.json",
            "compliance_ratchet.csv",
            "Reputation Ratchet",
        ),
        (
            "basic/scenario_6_enforcement_cycles.json",
            "compliance_oscillation.csv",
            "Enforcement Cycles",
        ),
    ]

    for scenario_file, csv_name, label in scenarios:
        print(f"Running {label} ({args.runs} seeds)...", flush=True)
        config = load_scenario(scenario_file)
        result = run_monte_carlo(config, n_runs=args.runs)
        out_path = out_dir / csv_name
        write_csv(out_path, result.step_compliance)
        print(
            f"  -> {out_path}  (final compliance: {result.final_compliance.mean:.1%})"
        )


if __name__ == "__main__":
    main()
