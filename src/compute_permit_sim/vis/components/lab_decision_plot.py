import solara
import pandas as pd
from matplotlib.figure import Figure
import numpy as np
from compute_permit_sim.core.constants import CHART_COLOR_MAP


@solara.component
def LabDecisionPlot(agents_df: pd.DataFrame, audit_prob: float, penalty: float):
    """Scatter plot of Economic Value vs Risk Profile with Deterrence Frontier.

    Theoretical Frontier: p * B = g
    (penalty * detection_prob * risk_profile) = economic_value

    Rearranging for y=risk_profile:
    risk_profile = economic_value / (penalty * detection_prob)

    Args:
        agents_df: DataFrame containing agent state.
        audit_prob: Current effective detection probability.
        penalty: Current penalty amount.
    """
    if agents_df is None or agents_df.empty:
        solara.Markdown("No Agent Data")
        return

    # Create Figure
    fig = Figure(figsize=(6, 5), dpi=100)
    ax = fig.subplots()

    # Extract data
    x = agents_df["revenue"]  # revenue matches economic_value for this plot context
    y = agents_df.get(
        "risk_profile", [1.0] * len(agents_df)
    )  # If not in snapshot, assume 1.0 or need to fix snapshot
    # Wait, risk_profile might not be in the snapshot! Check schema.
    # AgentSnapshot has: id, capacity, has_permit, used_compute, reported_compute, is_compliant...
    # It does NOT have risk_profile or economic_value constants if they are static.
    # We might need to fetch them from the model or assume they are static.
    # BUT, the user wants to see them.
    # If they are not in the dataframe, we can't plot them easily for a "snapshot".
    # However, 'revenue' field in snapshot is 'gross economic value generated'.
    # So 'revenue' == 'economic_value' (roughly, if they ran).
    # What about risk_profile?
    # We need to expose risk_profile in the AgentSnapshot.

    # Let's assume for now we need to Fix the Schema first or this plot is impossible.
    # User instruction: "Fix the Schema Leak: Ensure SimulationEngine.step uses the AgentSnapshot...".
    # Implementation Plan says "LabDecisionPlot ... Scatter plot of economic_value (x) vs risk_profile (y)".
    # I should check if I can add these fields to AgentSnapshot.

    # Temporary fallback: If column missing, plot dummy or try to recover.
    # But better to fix the schema.

    # Let's write this file assuming the columns EXIST, and I will go update the schema/model wrapper next.

    colors = agents_df["is_compliant"].map(
        {True: CHART_COLOR_MAP["green"], False: CHART_COLOR_MAP["red"]}
    )

    ax.scatter(x, y, c=colors, alpha=0.7, edgecolors="w", s=80)

    # Deterrence Line
    # y = x / (penalty * audit_prob)
    if penalty > 0 and audit_prob > 0:
        x_line = np.linspace(x.min(), x.max(), 100)
        y_line = x_line / (penalty * audit_prob)
        ax.plot(x_line, y_line, color="gray", linestyle="--", label="Indifference Line")

    ax.set_xlabel("Economic Value (Incentive)")
    ax.set_ylabel("Risk Profile (Sensitivity)")
    ax.set_title("Deterrence Frontier")
    ax.grid(True, alpha=0.3)

    # Styling
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    solara.FigureMatplotlib(fig)
