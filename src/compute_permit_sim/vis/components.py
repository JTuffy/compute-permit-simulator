"""Shared UI components for the Compute Permit Simulator."""

import solara
from matplotlib.figure import Figure


@solara.component
def RangeView(label: str, min_val: float, max_val: float):
    """Read-only display of a min-max range.

    Args:
        label: Descriptive label for the range.
        min_val: Current minimum value.
        max_val: Current maximum value.
    """
    solara.Markdown(f"*{label}*")
    solara.InputFloat(label="Min", value=min_val, disabled=True)
    solara.InputFloat(label="Max", value=max_val, disabled=True)


@solara.component
def RangeController(label: str, min_reactive, max_reactive):
    """Interactive control for a min-max range using reactive variables.

    Args:
        label: Descriptive label for the range.
        min_reactive: Solara reactive variable for the minimum value.
        max_reactive: Solara reactive variable for the maximum value.
    """
    solara.Markdown(f"*{label}*")
    solara.InputFloat(label="Min", value=min_reactive)
    solara.InputFloat(label="Max", value=max_reactive)


@solara.component
def QuantitativeScatterPlot(agents_df):
    """Scatter plot of Reported (X) vs True (Y) compute for risk analysis.

    Args:
        agents_df: pandas DataFrame containing agent snapshots with True_Compute,
                  Reported_Compute, Compliant, and Caught columns.
    """
    if agents_df is None or agents_df.empty:
        solara.Markdown("No data for scatter plot.")
        return

    # Extract data
    true_compute = agents_df["True_Compute"]
    reported_compute = agents_df["Reported_Compute"]

    fig = Figure(figsize=(6, 5))
    ax = fig.subplots()

    # Color coding logic
    # Default is blue
    colors = []
    # sizes = []

    # We need access to status columns.
    # agents_df is a DataFrame.
    # Check if we have the columns
    has_status = "Compliant" in agents_df.columns and "Caught" in agents_df.columns

    if has_status:
        for _, row in agents_df.iterrows():
            if row["Caught"]:
                colors.append("black")  # Caught
            elif not row["Compliant"]:
                colors.append("red")  # Cheating successfully
            else:
                colors.append("green")  # Compliant
    else:
        colors = "blue"

    # Simple scatter
    ax.scatter(
        reported_compute,
        true_compute,
        c=colors,
        alpha=0.6,
        edgecolors="k",
        label="Labs",
    )

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
