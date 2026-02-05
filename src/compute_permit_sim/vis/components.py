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
    with solara.Row():
        solara.InputFloat(label="Min", value=min_reactive, continuous_update=True)
        solara.InputFloat(label="Max", value=max_reactive, continuous_update=True)


@solara.component
def QuantitativeScatterPlot(agents_df):
    """Scatter plot of Reported (X) vs True (Y) compute for risk analysis.

    Args:
        agents_df: pandas DataFrame containing agent snapshots with Used Compute,
                  Reported Compute, Compliant, and Caught columns.
    """
    if agents_df is None or agents_df.empty:
        solara.Markdown("No data for scatter plot.")
        return

    # Extract data
    true_compute = agents_df["used_compute"]
    reported_compute = agents_df["reported_compute"]

    fig = Figure(figsize=(6, 5))
    ax = fig.subplots()

    # Color coding logic
    # Default is blue
    colors = []
    # sizes = []

    # We need access to status columns.
    # agents_df is a DataFrame.
    # Check if we have the columns
    has_status = (
        "is_compliant" in agents_df.columns and "was_caught" in agents_df.columns
    )

    if has_status:
        for _, row in agents_df.iterrows():
            if row["was_caught"]:
                colors.append("black")  # Caught
            elif not row["is_compliant"]:
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


@solara.component
def AuditTargetingPlot(agents_df):
    """Bar chart showing audit rates by compliance status.

    Helps regulators understand: Is our risk-based audit strategy
    actually catching the right people?
    """
    if agents_df is None or agents_df.empty:
        solara.Markdown("No data for audit targeting plot.")
        return

    # Check required columns
    required_cols = ["is_compliant", "was_audited"]
    if not all(col in agents_df.columns for col in required_cols):
        solara.Markdown("Missing required columns for audit plot.")
        return

    # Calculate audit rates by compliance status
    compliant_agents = agents_df[agents_df["is_compliant"]]
    noncompliant_agents = agents_df[~agents_df["is_compliant"]]

    compliant_audit_rate = (
        compliant_agents["was_audited"].mean() if len(compliant_agents) > 0 else 0
    )
    noncompliant_audit_rate = (
        noncompliant_agents["was_audited"].mean() if len(noncompliant_agents) > 0 else 0
    )

    # Create figure
    fig = Figure(figsize=(5, 4))
    ax = fig.subplots()

    categories = ["Compliant", "Non-Compliant"]
    rates = [compliant_audit_rate * 100, noncompliant_audit_rate * 100]
    colors = ["#4CAF50", "#F44336"]

    bars = ax.bar(categories, rates, color=colors, alpha=0.8, edgecolor="black")

    # Add value labels on bars
    for bar, rate in zip(bars, rates):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{rate:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_ylabel("Audit Rate (%)")
    ax.set_title("Audit Targeting Effectiveness")
    ax.set_ylim(0, max(rates) * 1.2 if max(rates) > 0 else 10)
    ax.grid(True, alpha=0.3, axis="y")

    # Add counts as annotation
    n_compliant = len(compliant_agents)
    n_noncompliant = len(noncompliant_agents)
    ax.text(
        0.02,
        0.98,
        f"n={n_compliant} compliant, {n_noncompliant} non-compliant",
        transform=ax.transAxes,
        fontsize=8,
        verticalalignment="top",
        alpha=0.7,
    )

    fig.tight_layout()
    solara.FigureMatplotlib(fig)


@solara.component
def PayoffByStrategyPlot(agents_df):
    """Bar chart comparing average net value by strategy outcome.

    Shows regulators: Does cheating actually pay? Is the penalty high enough?
    """
    if agents_df is None or agents_df.empty:
        solara.Markdown("No data for payoff plot.")
        return

    # Check required columns
    required_cols = ["is_compliant", "was_caught", "step_profit"]
    if not all(col in agents_df.columns for col in required_cols):
        solara.Markdown("Missing required columns for payoff plot.")
        return

    # Categorize agents
    compliant = agents_df[agents_df["is_compliant"]]
    cheated_caught = agents_df[~agents_df["is_compliant"] & agents_df["was_caught"]]
    cheated_uncaught = agents_df[
        ~agents_df["is_compliant"] & ~agents_df["was_caught"]
    ]  # Calculate average payoffs
    avg_compliant = compliant["step_profit"].mean() if len(compliant) > 0 else 0
    avg_caught = cheated_caught["step_profit"].mean() if len(cheated_caught) > 0 else 0
    avg_uncaught = (
        cheated_uncaught["step_profit"].mean() if len(cheated_uncaught) > 0 else 0
    )

    # Create figure
    fig = Figure(figsize=(5, 4))
    ax = fig.subplots()

    categories = ["Compliant", "Caught", "Uncaught"]
    payoffs = [avg_compliant, avg_caught, avg_uncaught]
    colors = ["#4CAF50", "#000000", "#F44336"]
    counts = [len(compliant), len(cheated_caught), len(cheated_uncaught)]

    bars = ax.bar(categories, payoffs, color=colors, alpha=0.8, edgecolor="black")

    # Add value labels on bars
    for bar, payoff, count in zip(bars, payoffs, counts):
        y_pos = bar.get_height()
        label_y = (
            y_pos + 0.02 * abs(max(payoffs) - min(payoffs))
            if y_pos >= 0
            else y_pos - 0.05 * abs(max(payoffs) - min(payoffs))
        )
        va = "bottom" if y_pos >= 0 else "top"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            label_y,
            f"${payoff:.2f}\n(n={count})",
            ha="center",
            va=va,
            fontsize=9,
            fontweight="bold",
        )

    ax.set_ylabel("Avg Net Value ($)")
    ax.set_title("Payoff by Strategy")
    ax.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="y")

    # Adjust y limits to show labels
    y_min = min(0, min(payoffs) * 1.3)
    y_max = max(payoffs) * 1.3 if max(payoffs) > 0 else 1
    ax.set_ylim(y_min, y_max)

    fig.tight_layout()
    solara.FigureMatplotlib(fig)


@solara.component
def LabDecisionPlot(agents_df, audit_prob: float, penalty: float):
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
    import numpy as np
    from compute_permit_sim.core.constants import CHART_COLOR_MAP

    if agents_df is None or agents_df.empty:
        solara.Markdown("No Agent Data")
        return

    # Check required columns
    required_cols = ["economic_value", "risk_profile", "is_compliant"]
    if not all(col in agents_df.columns for col in required_cols):
        solara.Markdown(
            "Missing data for decision plot (need economic_value/risk_profile)."
        )
        return

    # Create Figure
    fig = Figure(figsize=(6, 5), dpi=100)
    ax = fig.subplots()

    # Extract data
    x = agents_df["economic_value"]
    y = agents_df["risk_profile"]

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
    ax.legend()

    solara.FigureMatplotlib(fig)


@solara.component
def WealthDivergencePlot(
    compliant_history: list[float], non_compliant_history: list[float]
):
    """Line chart showing Total Wealth of Compliant vs Non-Compliant agents over time.

    Also tracks the "Criminal Premium" (Wealth Gap).
    """
    import numpy as np
    from compute_permit_sim.core.constants import CHART_COLOR_MAP
    from matplotlib.figure import Figure

    # Guard against empty data
    if not compliant_history and not non_compliant_history:
        solara.Markdown("No Wealth Data")
        return

    # Create figure
    fig = Figure(figsize=(8, 4), dpi=100)
    ax = fig.subplots()

    steps = list(range(1, len(compliant_history) + 1))

    # Plot lines
    ax.plot(
        steps,
        compliant_history,
        label="Compliant Total Wealth",
        color=CHART_COLOR_MAP["green"],
        linewidth=2.5,
        alpha=0.9,
    )
    ax.plot(
        steps,
        non_compliant_history,
        label="Non-Compliant Total Wealth",
        color=CHART_COLOR_MAP["red"],
        linewidth=2.5,
        alpha=0.9,
    )

    # Styling
    ax.set_xlabel("Step", fontsize=10)
    ax.set_ylabel("Total Wealth ($)", fontsize=10)
    ax.set_title("Wealth Divergence: Does Crime Pay?")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.25, linestyle="--")

    # Cleaner spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    solara.FigureMatplotlib(fig)
