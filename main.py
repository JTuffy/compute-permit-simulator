"""Main entry point for the simulation."""

from cpm_simulator.model import ComputePermitMarketModel


def main() -> None:
    """Run a simple simulation execution."""
    print("Initializing aisc-cm-simulator...")
    model = ComputePermitMarketModel(n_agents=10)
    steps = 10
    print(f"Running simulation for {steps} steps...")
    for _ in range(steps):
        model.step()

    # Calculate final compliance rate
    final_compliance = model.datacollector.get_model_vars_dataframe()["Compliance_Rate"].iloc[-1]
    print(f"Simulation complete. Final Compliance Rate: {final_compliance:.2%}")


if __name__ == "__main__":
    main()
