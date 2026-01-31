"""Shared UI components for the Compute Permit Simulator."""

import solara
from matplotlib.figure import Figure


@solara.component
def RangeView(label: str, min_val: float, max_val: float):
    """Read-only display of a min-max range."""
    solara.Markdown(f"*{label}*")
    solara.InputFloat(label="Min", value=min_val, disabled=True)
    solara.InputFloat(label="Max", value=max_val, disabled=True)


@solara.component
def RangeController(label: str, min_reactive, max_reactive):
    """Interactive control for a min-max range."""
    solara.Markdown(f"*{label}*")
    solara.InputFloat(label="Min", value=min_reactive)
    solara.InputFloat(label="Max", value=max_reactive)


@solara.component
def QuantitativeScatterPlot(agents_df):
    """Scatter plot of Reported (X) vs True (Y) compute."""
    if agents_df is None or agents_df.empty:
        solara.Markdown("No data for scatter plot.")
        return

    # Extract data
    true_compute = agents_df["True_Compute"]
    reported_compute = agents_df["Reported_Compute"]

    fig = Figure(figsize=(6, 5))
    ax = fig.subplots()

    # Simple scatter
    ax.scatter(reported_compute, true_compute, alpha=0.6, edgecolors="b", label="Labs")

    # Diagonal Line (True = Reported) aka "Honest Reporting"
    max_val = (
        max(true_compute.max(), reported_compute.max())
        if not true_compute.empty
        else 1.0
    )
    ax.plot([0, max_val], [0, max_val], "k--", alpha=0.5, label="Honesty (y=x)")

    ax.set_xlabel("Reported Compute (r)")
    ax.set_ylabel("True Compute (q)")
    ax.set_title("Risk Design: True vs Reported")
    ax.legend()
    ax.grid(True, alpha=0.3)

    solara.FigureMatplotlib(fig)
