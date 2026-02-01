"""Entry point for the Compute Permit Simulator."""

import json
from pathlib import Path

from compute_permit_sim.infrastructure.model import ComputePermitModel
from compute_permit_sim.schemas import ScenarioConfig


def run_scenario(name: str, config_dict: dict, steps: int = 10) -> None:
    """Run a single scenario.

    Args:
        name: Scenario name.
        config_dict: Dictionary of parameters from JSON.
        steps: Number of steps to run.
    """
    # Transform flat JSON into structured config
    # Transform flat JSON into structured config
    # Prefer new keys, fallback to defaults or old keys if necessary

    fpr = config_dict.get("false_positive_rate")
    if fpr is None:
        fpr = config_dict.get("signal_fpr", 0.1)

    fnr = config_dict.get("false_negative_rate")
    if fnr is None:
        # If FNR missing, try signal_tpr
        tpr = config_dict.get("signal_tpr")
        if tpr is not None:
            fnr = 1.0 - tpr
        else:
            fnr = 0.1

    audit_config = {
        "base_prob": config_dict.get("base_audit_prob"),
        "high_prob": config_dict.get("high_audit_prob"),
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
        "penalty_amount": config_dict.get("penalty"),
    }

    market_config = {"token_cap": config_dict.get("token_cap")}

    scenario_config = ScenarioConfig(
        name=name,
        description=config_dict.get("description", ""),
        n_agents=config_dict.get("n_agents"),
        steps=steps,  # Not in JSON, passed as arg or constant
        audit=audit_config,
        market=market_config,
        # Lab config uses defaults if not present
    )
    print(f"--- Running {name}: {scenario_config.description} ---")
    model = ComputePermitModel(config=scenario_config)

    for _ in range(scenario_config.steps):
        model.step()

    # Final stats
    df = model.datacollector.get_model_vars_dataframe()
    final_compliance = df["Compliance_Rate"].iloc[-1]
    final_price = df["Price"].iloc[-1]
    print(f"Results for {name}:")
    print(f"  Final Compliance Rate: {final_compliance:.2%}")
    print(f"  Final Market Price:    {final_price:.2f}")
    print("\n")


def main() -> None:
    """Load scenarios and run them."""
    scenario_path = Path("scenarios/config.json")
    if not scenario_path.exists():
        print("No scenario config found.")
        return

    with open(scenario_path, "r") as f:
        scenarios = json.load(f)

    for name, config in scenarios.items():
        run_scenario(name, config)


if __name__ == "__main__":
    main()
