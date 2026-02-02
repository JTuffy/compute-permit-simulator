"""Excel export functionality for simulation runs.

Exports run data to Excel with multiple sheets:
- Config: All simulation parameters
- Summary: Key metrics and time series data
- Agent Details: Full agent snapshot from last step
- Graphs: Embedded matplotlib figures
"""

import io

import pandas as pd
import xlsxwriter
import matplotlib

matplotlib.use("Agg")  # Force non-interactive backend for thread safety
from matplotlib.figure import Figure


def export_run_to_excel(run, output_path: str | None = None) -> str:
    """Export a simulation run to an Excel file with multiple sheets.

    Args:
        run: SimulationRun object containing config, steps, and metrics
        output_path: Optional path for the output file. If None, generates a
                     timestamped filename in the current directory.

    Returns:
        Path to the created Excel file.
    """
    if output_path is None:
        import os

        os.makedirs("outputs", exist_ok=True)
        output_path = f"outputs/simulation_run_{run.id}.xlsx"

    # Create workbook with xlsxwriter for image embedding support
    workbook = xlsxwriter.Workbook(output_path)

    # Define formats
    header_format = workbook.add_format(
        {"bold": True, "bg_color": "#2196F3", "font_color": "white", "border": 1}
    )
    section_format = workbook.add_format(
        {"bold": True, "bg_color": "#E3F2FD", "border": 1}
    )
    data_format = workbook.add_format({"border": 1})
    number_format = workbook.add_format({"border": 1, "num_format": "0.00"})
    percent_format = workbook.add_format({"border": 1, "num_format": "0.0%"})

    try:
        # === Sheet 1: Configuration ===
        config_sheet = workbook.add_worksheet("Configuration")
        _write_config_sheet(config_sheet, run.config, header_format, data_format)

        # === Sheet 2: Summary ===
        summary_sheet = workbook.add_worksheet("Summary")
        _write_summary_sheet(
            summary_sheet,
            run,
            header_format,
            section_format,
            data_format,
            number_format,
            percent_format,
        )

        # === Sheet 3: Agent Details (Last Step) ===
        if run.steps:
            agents_sheet = workbook.add_worksheet("Agent Details")
            _write_agents_sheet(
                agents_sheet, run.steps[-1], header_format, data_format, number_format
            )

        # === Sheet 4: Graphs ===
        graphs_sheet = workbook.add_worksheet("Graphs")
        _write_graphs_sheet(graphs_sheet, run, workbook)

    finally:
        workbook.close()

    return output_path


def _write_config_sheet(sheet, config, header_format, data_format):
    """Write configuration parameters to sheet."""
    sheet.set_column("A:A", 25)
    sheet.set_column("B:B", 20)

    row = 0

    # General
    sheet.write(row, 0, "General Parameters", header_format)
    sheet.write(row, 1, "", header_format)
    row += 1

    params = [
        ("Name", config.name),
        ("Description", config.description or ""),
        ("Steps", config.steps),
        ("Number of Agents", config.n_agents),
        ("Seed", config.seed if config.seed else "None"),
    ]
    for label, value in params:
        sheet.write(row, 0, label, data_format)
        sheet.write(row, 1, value, data_format)
        row += 1

    row += 1

    # Market
    sheet.write(row, 0, "Market Parameters", header_format)
    sheet.write(row, 1, "", header_format)
    row += 1

    market_params = [
        ("Token Cap", config.market.token_cap),
    ]
    for label, value in market_params:
        sheet.write(row, 0, label, data_format)
        sheet.write(row, 1, value, data_format)
        row += 1

    row += 1

    # Audit
    sheet.write(row, 0, "Audit Parameters", header_format)
    sheet.write(row, 1, "", header_format)
    row += 1

    audit_params = [
        ("Penalty Amount ($)", config.audit.penalty_amount),
        ("Base Probability (π₀)", config.audit.base_prob),
        ("High Probability (π₁)", config.audit.high_prob),
        ("False Positive Rate", config.audit.false_positive_rate),
        ("False Negative Rate", config.audit.false_negative_rate),
        ("Backcheck Probability", config.audit.backcheck_prob),
        ("Whistleblower Probability", config.audit.whistleblower_prob),
    ]
    for label, value in audit_params:
        sheet.write(row, 0, label, data_format)
        sheet.write(row, 1, value, data_format)
        row += 1

    row += 1

    # Lab Generation
    sheet.write(row, 0, "Lab Generation", header_format)
    sheet.write(row, 1, "", header_format)
    row += 1

    lab_params = [
        ("Economic Value Min", config.lab.economic_value_min),
        ("Economic Value Max", config.lab.economic_value_max),
        ("Risk Profile Min", config.lab.risk_profile_min),
        ("Risk Profile Max", config.lab.risk_profile_max),
        ("Capacity Min", config.lab.capacity_min),
        ("Capacity Max", config.lab.capacity_max),
        ("Capability Value (Vb)", config.lab.capability_value),
        ("Racing Factor (cr)", config.lab.racing_factor),
        ("Reputation Sensitivity (β)", config.lab.reputation_sensitivity),
        ("Audit Coefficient", config.lab.audit_coefficient),
    ]
    for label, value in lab_params:
        sheet.write(row, 0, label, data_format)
        sheet.write(row, 1, value, data_format)
        row += 1


def _write_summary_sheet(
    sheet,
    run,
    header_format,
    section_format,
    data_format,
    number_format,
    percent_format,
):
    """Write summary metrics to sheet."""
    sheet.set_column("A:A", 25)
    sheet.set_column("B:B", 15)

    row = 0

    # Run Info
    sheet.write(row, 0, "Run Information", header_format)
    sheet.write(row, 1, "", header_format)
    row += 1

    sheet.write(row, 0, "Run ID", data_format)
    sheet.write(row, 1, run.id, data_format)
    row += 1

    sheet.write(row, 0, "Total Steps", data_format)
    sheet.write(row, 1, len(run.steps), data_format)
    row += 1

    row += 1

    # Key Metrics
    sheet.write(row, 0, "Final Metrics", header_format)
    sheet.write(row, 1, "", header_format)
    row += 1

    if run.metrics:
        metrics = [
            (
                "Final Compliance",
                run.metrics.get("final_compliance", 0),
                percent_format,
            ),
            ("Final Price ($)", run.metrics.get("final_price", 0), number_format),
            ("Fraud Detected", run.metrics.get("fraud_detected", 0), data_format),
            ("Fraud Undetected", run.metrics.get("fraud_undetected", 0), data_format),
        ]
        for label, value, fmt in metrics:
            sheet.write(row, 0, label, data_format)
            sheet.write(row, 1, value, fmt)
            row += 1

    row += 1

    # Time Series Data
    sheet.write(row, 0, "Time Series Data", header_format)
    sheet.write(row, 1, "Compliance", header_format)
    sheet.write(row, 2, "Price", header_format)
    row += 1

    for i, step in enumerate(run.steps):
        # Calculate compliance for this step
        compliant_count = sum(1 for a in step.agents if a.get("Compliant"))
        total = len(step.agents)
        compliance = compliant_count / total if total > 0 else 0
        price = step.market.get("price", 0)

        sheet.write(row, 0, f"Step {i}", data_format)
        sheet.write(row, 1, compliance, percent_format)
        sheet.write(row, 2, price, number_format)
        row += 1


def _write_agents_sheet(sheet, last_step, header_format, data_format, number_format):
    """Write agent details from last step to sheet."""
    if not last_step.agents:
        sheet.write(0, 0, "No agent data available")
        return

    # Convert to DataFrame
    agents_df = pd.DataFrame(last_step.agents)

    # Define columns to export
    cols = [
        "ID",
        "Value",
        "Net_Value",
        "Capacity",
        "True_Compute",
        "Reported_Compute",
        "Compliant",
        "Audited",
        "Caught",
        "Penalty",
        "Wealth",
    ]
    valid_cols = [c for c in cols if c in agents_df.columns]

    # Write headers
    for col_idx, col_name in enumerate(valid_cols):
        sheet.write(0, col_idx, col_name, header_format)

    # Set column widths
    for col_idx in range(len(valid_cols)):
        sheet.set_column(col_idx, col_idx, 15)

    # Write data
    for row_idx, (_, row) in enumerate(agents_df[valid_cols].iterrows()):
        for col_idx, value in enumerate(row):
            if isinstance(value, (int, float)):
                sheet.write(row_idx + 1, col_idx, value, number_format)
            else:
                sheet.write(row_idx + 1, col_idx, str(value), data_format)


def _write_graphs_sheet(sheet, run, workbook):
    """Write embedded graphs to sheet."""
    if not run.steps:
        sheet.write(0, 0, "No data for graphs")
        return

    # Calculate time series for the graphs
    compliance_series = []
    price_series = []

    for step in run.steps:
        compliant_count = sum(1 for a in step.agents if a.get("Compliant"))
        total = len(step.agents)
        compliance_series.append(compliant_count / total if total > 0 else 0)
        price_series.append(step.market.get("price", 0))

    # Create and embed compliance graph
    sheet.write(0, 0, "Compliance Over Time")
    comp_fig = _create_time_series_figure(compliance_series, "Compliance", "#4CAF50")
    comp_img = _fig_to_bytes(comp_fig)
    sheet.insert_image(1, 0, "compliance.png", {"image_data": comp_img})

    # Create and embed price graph (offset to the right)
    sheet.write(0, 8, "Price Over Time")
    price_fig = _create_time_series_figure(price_series, "Price ($)", "#2196F3")
    price_img = _fig_to_bytes(price_fig)
    sheet.insert_image(1, 8, "price.png", {"image_data": price_img})

    # If we have agents in last step, create scatter plot
    if run.steps[-1].agents:
        agents_df = pd.DataFrame(run.steps[-1].agents)
        if (
            "True_Compute" in agents_df.columns
            and "Reported_Compute" in agents_df.columns
        ):
            sheet.write(25, 0, "True vs Reported Compute (Last Step)")
            scatter_fig = _create_scatter_figure(agents_df)
            scatter_img = _fig_to_bytes(scatter_fig)
            sheet.insert_image(26, 0, "scatter.png", {"image_data": scatter_img})


def _create_time_series_figure(data, label, color):
    """Create a simple time series figure for embedding."""
    fig = Figure(figsize=(5, 3), dpi=100)
    ax = fig.subplots()

    ax.plot(data, color=color, linewidth=2)
    ax.set_xlabel("Step")
    ax.set_ylabel(label)
    ax.set_title(f"{label} Over Time")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    return fig


def _create_scatter_figure(agents_df):
    """Create scatter plot of true vs reported compute."""
    fig = Figure(figsize=(5, 4), dpi=100)
    ax = fig.subplots()

    # Color by compliance status
    colors = []
    has_status = "Compliant" in agents_df.columns and "Caught" in agents_df.columns
    if has_status:
        for _, row in agents_df.iterrows():
            if row.get("Caught"):
                colors.append("black")
            elif not row.get("Compliant"):
                colors.append("red")
            else:
                colors.append("green")
    else:
        colors = "blue"

    ax.scatter(
        agents_df["Reported_Compute"],
        agents_df["True_Compute"],
        c=colors,
        alpha=0.6,
        edgecolors="k",
    )

    max_val = max(
        agents_df["True_Compute"].max(),
        agents_df["Reported_Compute"].max(),
    )
    ax.plot([0, max_val], [0, max_val], "k--", alpha=0.5, label="Honest (y=x)")

    ax.set_xlabel("Reported Compute")
    ax.set_ylabel("True Compute")
    ax.set_title("True vs Reported Compute")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    return fig


def _fig_to_bytes(fig) -> io.BytesIO:
    """Convert matplotlib figure to bytes for embedding in Excel."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    return buf
