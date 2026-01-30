"""Deterrence Heatmap Visualization."""

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from tqdm import tqdm

from ..infrastructure.model import ComputePermitModel
from ..schemas import AuditConfig, MarketConfig, ScenarioConfig


def generate_heatmap(
    penalty_range: list[float],
    prob_range: list[float],
    n_agents: int = 20,
    steps: int = 10,
    output_file: str = "deterrence_heatmap.png",
) -> None:
    """Generate a heatmap of Compliance Rate (P vs Detection Prob).

    Args:
        penalty_range: List of penalty values (X-axis).
        prob_range: List of detection probability values (Y-axis).
        n_agents: Agents in sim.
        steps: Steps per sim.
        output_file: Path to save image.
    """
    compliance_grid = np.zeros((len(prob_range), len(penalty_range)))

    print("Generating Deterrence Heatmap...")
    for i, p_det in enumerate(tqdm(prob_range, desc="Probabilities")):
        for j, penalty in enumerate(penalty_range):
            # Construct Config
            # Note: We need to force p_det. In our model, p_eff depends on signal.
            # To simulate exact 'p', we can set pi_0 = pi_1 = p_det

            audit_config = {
                "base_prob": p_det,
                "high_prob": p_det,
                "signal_fpr": 0.5,  # Irrelevant if pi_0=pi_1
                "signal_tpr": 0.5,
                "penalty_amount": penalty,
            }

            config = ScenarioConfig(
                n_agents=n_agents,
                steps=steps,
                audit=audit_config,
                market={"token_cap": n_agents * 0.5},  # Cap at 50%
                seed=42,
            )

            model = ComputePermitModel(config)
            for _ in range(steps):
                model.step()

            df = model.datacollector.get_model_vars_dataframe()
            # Average compliance of last 5 steps to stabilize
            final_compliance = df["Compliance_Rate"].tail(5).mean()
            compliance_grid[i, j] = final_compliance

    # Plot
    plt.figure(figsize=(10, 8))
    ax = sns.heatmap(
        compliance_grid,
        xticklabels=[f"{x:.2f}" for x in penalty_range],
        yticklabels=[f"{y:.2f}" for y in prob_range],
        annot=True,
        fmt=".2f",
        cmap="RdYlGn",  # Red (Low) to Green (High Compliance)
        vmin=0,
        vmax=1,
    )
    ax.invert_yaxis()  # Put low prob at bottom
    plt.xlabel("Penalty (P)")
    plt.ylabel("Detection Probability (p)")
    plt.title("Deterrence Heatmap: Compliance Rate")

    plt.savefig(output_file)
    print(f"Heatmap saved to {output_file}")


if __name__ == "__main__":
    # Recommended range from spec: P 0.2->0.8, p 0.25->0.75
    penalties = np.linspace(0.1, 1.0, 10)
    probs = np.linspace(0.1, 1.0, 10)

    generate_heatmap(list(penalties), list(probs))
