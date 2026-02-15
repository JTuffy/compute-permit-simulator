"""Excel export functionality for simulation runs.

Exports run data to Excel with multiple sheets:
- Config: All simulation parameters (auto-generated from schema)
- Summary: Key metrics and time series data
- Agent Details: Full agent snapshot from last step
- Graphs: Embedded matplotlib figures
"""

import io
import os

import pandas as pd
import xlsxwriter
from pydantic import BaseModel

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.schemas.config import ScenarioConfig
from compute_permit_sim.services.metrics import calculate_compliance
from compute_permit_sim.vis.plotting import (
    plot_deterrence_frontier,
    plot_payoff_distribution,
    plot_scatter,
    plot_time_series,
)

# Sub-model grouping: maps ScenarioConfig nested keys to display section headers
_SECTION_LABELS = {
    "audit": "Audit Parameters",
    "market": "Market Parameters",
    "lab": "Lab Generation",
}


def export_run_to_excel(run, output_path: str | None = None) -> str:
    """Export a simulation run to an Excel file with multiple sheets."""
    if output_path is None:
        os.makedirs("outputs", exist_ok=True)
        # Use simpler Config ID if available, otherwise timestamp
        fname = run.sim_id if run.sim_id else run.id
        output_path = f"outputs/simulation_run_{fname}.xlsx"

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


def _get_field_label(model_class, field_name: str) -> str:
    """Get human-readable label from json_schema_extra or fallback."""
    field_info = model_class.model_fields.get(field_name)
    if field_info is None:
        return field_name

    extra = field_info.json_schema_extra
    if extra and "ui_label" in extra:
        return extra["ui_label"]
    if field_info.description:
        return field_info.description
    return field_name.replace("_", " ").title()


def _write_config_section(
    sheet,
    model_class,
    data: dict,
    section_title: str,
    row: int,
    header_format,
    data_format,
) -> int:
    """Write a config section header and all its fields.

    Returns the next available row.
    """
    sheet.write(row, 0, section_title, header_format)
    sheet.write(row, 1, "", header_format)
    row += 1

    for field_name, value in data.items():
        label = _get_field_label(model_class, field_name)
        display_value = value if value is not None else "None"
        sheet.write(row, 0, label, data_format)
        sheet.write(row, 1, display_value, data_format)
        row += 1

    return row + 1  # blank spacer row


def _write_config_sheet(sheet, config, header_format, data_format):
    """Write configuration parameters to sheet — fully dynamic from Schema."""
    sheet.set_column("A:A", 30)
    sheet.set_column("B:B", 20)

    row = 0

    # 1. Top-level scalar fields
    top_level_data = {}
    for name, field_info in ScenarioConfig.model_fields.items():
        # Check if field type is a Pydantic model
        is_model = isinstance(field_info.annotation, type) and issubclass(
            field_info.annotation, BaseModel
        )
        if not is_model:
            top_level_data[name] = getattr(config, name, None)

    if top_level_data:
        row = _write_config_section(
            sheet,
            ScenarioConfig,
            top_level_data,
            "General Parameters",
            row,
            header_format,
            data_format,
        )

    # 2. Sub-models (Sections)
    for name, field_info in ScenarioConfig.model_fields.items():
        is_model = isinstance(field_info.annotation, type) and issubclass(
            field_info.annotation, BaseModel
        )
        if is_model:
            sub_config = getattr(config, name, None)
            if sub_config:
                # Use the field name as section title (capitalized) or ui_group if available
                extra = field_info.json_schema_extra or {}
                section_title = extra.get("ui_group", name.replace("_", " ").title())

                # Helper maps generic names to specific Excel section titles if needed
                # But dynamic title is better.

                row = _write_config_section(
                    sheet,
                    field_info.annotation,
                    sub_config.model_dump(),
                    section_title,
                    row,
                    header_format,
                    data_format,
                )


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
    # Prefer nicer Config ID
    display_id = run.sim_id if run.sim_id else run.id
    sheet.write(row, 1, display_id, data_format)
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
                run.metrics.final_compliance,
                percent_format,
            ),
            ("Final Price ($)", run.metrics.final_price, number_format),
            ("Total Cost", run.metrics.total_enforcement_cost, number_format),
            ("Deterrence Rate", run.metrics.deterrence_success_rate, percent_format),
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
        compliance = calculate_compliance(step.agents)
        price = step.market.price

        sheet.write(row, 0, f"Step {i}", data_format)
        sheet.write(row, 1, compliance, percent_format)
        sheet.write(row, 2, price, number_format)
        row += 1


def _write_agents_sheet(sheet, last_step, header_format, data_format, number_format):
    """Write agent details from last step to sheet."""
    if not last_step.agents:
        sheet.write(0, 0, "No agent data available")
        return

    # Convert to DataFrame properly from Pydantic models
    agents_df = pd.DataFrame([a.model_dump() for a in last_step.agents])

    # Define columns to export (using correct snake_case Pydantic field names)
    cols = [
        (ColumnNames.ID, "ID"),
        (ColumnNames.REVENUE, "Revenue"),
        (ColumnNames.STEP_PROFIT, "Step Profit"),
        (ColumnNames.CAPACITY, "Capacity"),
        (ColumnNames.USED_COMPUTE, "Used Compute"),
        (ColumnNames.REPORTED_COMPUTE, "Reported Compute"),
        (ColumnNames.IS_COMPLIANT, "Compliant"),
        (ColumnNames.WAS_AUDITED, "Audited"),
        (ColumnNames.WAS_CAUGHT, "Caught"),
        (ColumnNames.PENALTY_AMOUNT, "Penalty"),
        (ColumnNames.WEALTH, "Total Wealth"),
    ]

    valid_cols = []
    headers = []

    # Check which columns exist
    for field, header in cols:
        if field in agents_df.columns:
            valid_cols.append(field)
            headers.append(header)

    # Write headers
    for col_idx, header in enumerate(headers):
        sheet.write(0, col_idx, header, header_format)

    # Set column widths
    for col_idx in range(len(headers)):
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
        compliance_series.append(calculate_compliance(step.agents))
        price_series.append(step.market.price)

    # Create and embed compliance graph
    sheet.write(0, 0, "Compliance Over Time")
    comp_fig = plot_time_series(compliance_series, "Compliance", "green")
    comp_img = _fig_to_bytes(comp_fig)
    sheet.insert_image(1, 0, "compliance.png", {"image_data": comp_img})

    # Create and embed price graph (offset to the right)
    sheet.write(0, 8, "Price Over Time")
    price_fig = plot_time_series(price_series, "Price ($)", "blue")
    price_img = _fig_to_bytes(price_fig)
    sheet.insert_image(1, 8, "price.png", {"image_data": price_img})

    # If we have agents in last step, create scatter plot
    if run.steps[-1].agents:
        agents_df = pd.DataFrame([a.model_dump() for a in run.steps[-1].agents])
        # Check for numeric columns (snake_case)
        if (
            ColumnNames.USED_COMPUTE in agents_df.columns
            and ColumnNames.REPORTED_COMPUTE in agents_df.columns
        ):
            sheet.write(25, 0, "True vs Reported Compute (Last Step)")

            scatter_fig, ax = plot_scatter(
                agents_df,
                ColumnNames.REPORTED_COMPUTE,
                ColumnNames.USED_COMPUTE,
                "True vs Reported Compute",
                "Reported Compute",
                "True Compute",
                color_logic="compliance",
            )

            # Add y=x line locally
            max_val = max(
                agents_df[ColumnNames.USED_COMPUTE].max(),
                agents_df[ColumnNames.REPORTED_COMPUTE].max(),
            )
            ax.plot([0, max_val], [0, max_val], "k--", alpha=0.5, label="Honest (y=x)")
            ax.legend()
            scatter_fig.tight_layout()
            scatter_img = _fig_to_bytes(scatter_fig)
            sheet.insert_image(26, 0, "scatter.png", {"image_data": scatter_img})

            # Deterrence Frontier
            sheet.write(25, 8, "Deterrence Frontier (Value vs Risk)")
            det_fig, _ = plot_deterrence_frontier(agents_df)
            det_img = _fig_to_bytes(det_fig)
            sheet.insert_image(26, 8, "deterrence.png", {"image_data": det_img})

            # Payoff Distribution
            sheet.write(50, 0, "Payoff Analysis")
            payoff_fig, _ = plot_payoff_distribution(agents_df)
            payoff_img = _fig_to_bytes(payoff_fig)
            sheet.insert_image(51, 0, "payoff.png", {"image_data": payoff_img})


def _fig_to_bytes(fig) -> io.BytesIO:
    """Convert matplotlib figure to bytes for embedding in Excel."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    return buf
