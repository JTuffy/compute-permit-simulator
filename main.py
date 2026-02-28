"""Entry point for the Compute Permit Simulator."""

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
from compute_permit_sim.vis.export import export_run_to_csv, export_run_to_excel

# Configure logging for CLI
logger = logging.getLogger("compute_permit_sim.cli")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def run_scenario(config: ScenarioConfig) -> list[str] | None:
    """Run a single scenario.

    Args:
        config: Validated scenario configuration.
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

    import os

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


def main() -> None:
    """Load and run all scenarios from the specific directory."""
    from compute_permit_sim.services.config_manager import (
        list_scenarios,
        load_scenario,
    )

    scenarios = list_scenarios()
    if not scenarios:
        logger.info("No scenarios found in scenarios/ directory.")
        return

    logger.info(f"Found {len(scenarios)} scenarios.")
    all_generated_files = []
    for filename in scenarios:
        try:
            config = load_scenario(filename)
            files = run_scenario(config)
            if files:
                all_generated_files.extend(files)
        except Exception as e:
            logger.error(f"Failed to run {filename}: {e}")

    if all_generated_files:
        import time
        import zipfile

        bundle_timestamp = time.strftime("%Y%m%d_%H%M%S")
        bundle_name = f"outputs/simulation_bundle_{bundle_timestamp}.zip"

        try:
            with zipfile.ZipFile(bundle_name, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file in all_generated_files:
                    zipf.write(file, os.path.basename(file))
            print(
                f"Successfully bundled {len(all_generated_files)} files into {bundle_name}"
            )
        except Exception as e:
            print(f"Failed to create zip bundle: {e}")


if __name__ == "__main__":
    main()
