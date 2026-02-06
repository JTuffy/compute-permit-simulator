"""Entry point for the Compute Permit Simulator."""

import logging

from compute_permit_sim.schemas import ScenarioConfig
from compute_permit_sim.services.model_wrapper import ComputePermitModel

# Configure logging for CLI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def run_scenario(config: ScenarioConfig) -> None:
    """Run a single scenario.

    Args:
        config: Validated scenario configuration.
    """
    print(f"--- Running {config.name}: {config.description} ---")
    model = ComputePermitModel(config=config)

    for _ in range(config.steps):
        model.step()

    # Final stats
    df = model.datacollector.get_model_vars_dataframe()
    # Handle case where run might have failed or 0 steps
    if not df.empty:
        final_compliance = df["Compliance_Rate"].iloc[-1]
        final_price = df["Price"].iloc[-1]
        print(f"Results for {config.name}:")
        print(f"  Final Compliance Rate: {final_compliance:.2%}")
        print(f"  Final Market Price:    {final_price:.2f}")
    else:
        print(f"Results for {config.name}: No data collected.")
    print("\n")


def main() -> None:
    """Load and run all scenarios from the specific directory."""
    from compute_permit_sim.services.config_manager import (
        list_scenarios,
        load_scenario,
    )

    scenarios = list_scenarios()
    if not scenarios:
        print("No scenarios found in scenarios/ directory.")
        return

    print(f"Found {len(scenarios)} scenarios.")
    for filename in scenarios:
        try:
            config = load_scenario(filename)
            run_scenario(config)
        except Exception as e:
            print(f"Failed to run {filename}: {e}")


if __name__ == "__main__":
    main()
