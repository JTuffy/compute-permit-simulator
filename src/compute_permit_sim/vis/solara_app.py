"""Solara-based interactive dashboard for the Simulator."""

import matplotlib.pyplot as plt
import solara

from compute_permit_sim.infrastructure.model import ComputePermitModel
from compute_permit_sim.schemas import ScenarioConfig

# --- Reactive State ---
# Parameters
penalty = solara.reactive(0.5)
detection_prob = solara.reactive(0.1)  # Base probability
token_cap = solara.reactive(5)
n_agents = solara.reactive(20)

# Model State
model = solara.reactive(None)
step_count = solara.reactive(0)
compliance_history = solara.reactive([])
price_history = solara.reactive([])


def reset_model():
    """Re-initialize the model with current parameters."""
    audit_config = {
        "base_prob": detection_prob.value,
        "high_prob": detection_prob.value,  # Simplify for UI: pi_0 = pi_1
        "false_positive_rate": 0.1,
        "false_negative_rate": 0.1,
        "penalty_amount": penalty.value,
    }

    config = ScenarioConfig(
        name="Interactive",
        n_agents=n_agents.value,
        steps=100,
        audit=audit_config,
        market={"token_cap": float(token_cap.value)},
        seed=42,  # Fixed seed for reproducibility on reset? Or random?
        # Let's keep it fixed for specific experiments, or remove for randomness.
    )

    new_model = ComputePermitModel(config)
    model.value = new_model
    step_count.value = 0
    compliance_history.value = []
    price_history.value = []


def step_model():
    """Advance the model by one step."""
    if model.value is None:
        reset_model()

    model.value.step()
    step_count.value += 1

    # Update histories
    df = model.value.datacollector.get_model_vars_dataframe()
    if not df.empty:
        compliance_history.value = df["Compliance_Rate"].tolist()
        price_history.value = df["Price"].tolist()


# --- UI Components ---


@solara.component
def ComplianceChart():
    if not compliance_history.value:
        return solara.Markdown("No data yet.")

    # Matplotlib fig
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(compliance_history.value, label="Compliance Rate", color="green")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Steps")
    ax.set_ylabel("Compliance")
    ax.legend()
    ax.grid(True)

    solara.FigureMatplotlib(fig)


@solara.component
def PriceChart():
    if not price_history.value:
        return solara.Markdown("No data yet.")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(price_history.value, label="Market Price", color="blue")
    ax.set_xlabel("Steps")
    ax.set_ylabel("Price")
    ax.legend()
    ax.grid(True)

    solara.FigureMatplotlib(fig)


@solara.component
def Page():
    with solara.Sidebar():
        solara.Markdown("### Simulation Parameters")
        solara.SliderFloat("Penalty (P)", value=penalty, min=0.0, max=2.0)
        solara.SliderFloat("Detection Prob (p)", value=detection_prob, min=0.0, max=1.0)
        solara.SliderInt("Token Cap (Q)", value=token_cap, min=1, max=50)
        solara.SliderInt("N Agents", value=n_agents, min=5, max=50)

        solara.Button("Reset Model", on_click=reset_model, color="primary")
        solara.Button("Step", on_click=step_model)

    solara.Title("Compute Permit Market Simulator")

    with solara.Card("Metrics"):
        solara.Markdown(f"**Step:** {step_count.value}")
        if compliance_history.value:
            solara.Markdown(
                f"**Current Compliance:** {compliance_history.value[-1]:.2%}"
            )
            solara.Markdown(f"**Current Price:** {price_history.value[-1]:.2f}")

    with solara.Columns([1, 1]):
        with solara.Column():
            solara.Markdown("### Compliance Over Time")
            ComplianceChart()

        with solara.Column():
            solara.Markdown("### Market Price Over Time")
            PriceChart()


# Initialize on load if empty
if model.value is None:
    reset_model()
