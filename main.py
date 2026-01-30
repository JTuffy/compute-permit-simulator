from cpm_simulator.model import ComputePermitMarketModel

def main():
    print("Initializing aisc-cm-simulator...")
    model = ComputePermitMarketModel(N=10)
    steps = 10
    print(f"Running simulation for {steps} steps...")
    for i in range(steps):
        model.step()
    
    # Calculate final compliance rate
    final_compliance = model.datacollector.get_model_vars_dataframe()["Compliance_Rate"].iloc[-1]
    print(f"Simulation complete. Final Compliance Rate: {final_compliance:.2%}")

if __name__ == "__main__":
    main()
