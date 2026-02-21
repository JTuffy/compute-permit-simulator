"""Export functionality for simulation runs (Excel and CSV).

Exports run data to:
1. Excel with multiple sheets (Config, Summary, Agent Details, Graphs)
2. CSV with flattened step-by-step agent data and full configuration context.
"""

import io
import os

import pandas as pd
import xlsxwriter
from pydantic import BaseModel

from compute_permit_sim.schemas import AgentSnapshot, RunMetrics, ScenarioConfig
from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.services.metrics import calculate_compliance
from compute_permit_sim.vis.plotting import (
    plot_deterrence_frontier,
    plot_payoff_distribution,
    plot_scatter,
    plot_time_series,
)


def export_run_to_excel(run, output_path: str | None = None) -> str | bytes:
    """Export a simulation run to an Excel file.

    Args:
        run: The simulation run to export.
        output_path: File path to write to.
                     - If None (default): Generates a path in outputs/.
                     - If "": Returns bytes (in-memory).
                     - If valid path: Writes to that path.

    Returns:
        str (path) if written to file.
        bytes if output_path was empty string.
    """
    return_bytes = False

    if output_path == "":
        # Special flag for in-memory
        output = io.BytesIO()
        return_bytes = True
    elif output_path is None:
        os.makedirs("outputs", exist_ok=True)
        fname = run.sim_id if run.sim_id else run.id
        output_path = f"outputs/simulation_run_{fname}.xlsx"
        output = output_path
    else:
        output = output_path

    # Create workbook with xlsxwriter
    workbook = xlsxwriter.Workbook(output)

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

    if return_bytes:
        # output is BytesIO
        output.seek(0)
        return output.read()

    assert output_path is not None
    return output_path


def export_run_to_csv(run, output_path: str | None = None) -> str | bytes:
    """Export a simulation run to a flattened CSV file.

    Includes all configuration parameters in every row to ensure the file is
    self-describing and comprehensive for external analysis tools.

    Args:
        run: The simulation run to export.
        output_path: File path to write to (None=auto, ""=bytes).

    Returns:
        str (path) if written to file.
        bytes if output_path was empty string.
    """
    # 1. Flatten config to include in every row
    config_dict = run.config.model_dump()

    def _flatten_dict(d, prefix="config_"):
        items = []
        for k, v in d.items():
            new_key = f"{prefix}{k}"
            if isinstance(v, dict):
                items.extend(_flatten_dict(v, f"{new_key}_").items())
            else:
                items.append((new_key, v))
        return dict(items)

    flat_config = _flatten_dict(config_dict)

    # 2. Collect all agent-steps
    rows = []
    for step_res in run.steps:
        # Market data for this step
        market_data = {
            "run_id": run.id,
            "sim_id": run.sim_id,
            "step": step_res.step,
            "market_price": step_res.market.price,
            "market_supply": step_res.market.supply,
            **flat_config,
        }
        for agent in step_res.agents:
            row = market_data.copy()
            # Prefix agent fields for clarity
            agent_data = {f"agent_{k}": v for k, v in agent.model_dump().items()}
            row.update(agent_data)
            rows.append(row)

    if not rows:
        # Fallback if no steps were recorded
        df = pd.DataFrame([{"run_id": run.id, **flat_config}])
    else:
        df = pd.DataFrame(rows)

    if output_path == "":
        return df.to_csv(index=False).encode("utf-8")

    if output_path is None:
        os.makedirs("outputs", exist_ok=True)
        fname = run.sim_id if run.sim_id else run.id
        output_path = f"outputs/simulation_run_{fname}.csv"

    df.to_csv(output_path, index=False)
    return output_path


def _get_field_label(model_class, field_name: str) -> str:
    """Get human-readable label from json_schema_extra or fallback."""
    field_info = model_class.model_fields.get(field_name)
    if field_info is None:
        return field_name.replace("_", " ").title()

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
    """Write a config section header and all its fields."""
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

    # Basic Run Metadata
    sheet.write(row, 0, "Run ID", data_format)
    display_id = run.sim_id if run.sim_id else run.id
    sheet.write(row, 1, display_id, data_format)
    row += 1

    sheet.write(row, 0, "Total Steps", data_format)
    sheet.write(row, 1, len(run.steps), data_format)
    row += 2

    # Key Metrics (Dynamic from RunMetrics schema)
    sheet.write(row, 0, "Final Metrics", header_format)
    sheet.write(row, 1, "", header_format)
    row += 1

    if run.metrics:
        # Dynamically iterate over metrics fields
        for field_name, field_info in RunMetrics.model_fields.items():
            value = getattr(run.metrics, field_name)
            label = _get_field_label(RunMetrics, field_name)

            # Heuristic for formatting based on name
            fmt = number_format
            if "rate" in field_name or "compliance" in field_name:
                fmt = percent_format
            elif "price" in field_name or "cost" in field_name:
                fmt = number_format  # Could use currency format if added

            sheet.write(row, 0, label, data_format)
            sheet.write(row, 1, value, fmt)
            row += 1

    row += 2

    # Time Series Data
    sheet.write(row, 0, "Time Series Data", header_format)
    sheet.write(row, 1, "Compliance", header_format)
    sheet.write(row, 2, "Price", header_format)
    row += 1

    for i, step in enumerate(run.steps):
        compliance = calculate_compliance(step.agents)
        price = step.market.price

        sheet.write(row, 0, f"Step {i}", data_format)
        sheet.write(row, 1, compliance, percent_format)
        sheet.write(row, 2, price, number_format)
        row += 1


def _write_agents_sheet(sheet, last_step, header_format, data_format, number_format):
    """Write agent details from last step - dynamically."""
    if not last_step.agents:
        sheet.write(0, 0, "No agent data available")
        return

    # Convert to DataFrame
    agents_df = pd.DataFrame([a.model_dump() for a in last_step.agents])

    # Dynamic Column Headers from AgentSnapshot schema
    headers = []
    valid_cols = []

    for field_name, field_info in AgentSnapshot.model_fields.items():
        if field_name in agents_df.columns:
            headers.append(_get_field_label(AgentSnapshot, field_name))
            valid_cols.append(field_name)

    # Write headers
    for col_idx, header in enumerate(headers):
        sheet.write(0, col_idx, header, header_format)
        sheet.set_column(col_idx, col_idx, 15)  # Set width

    # Write data
    for row_idx, (_, row) in enumerate(agents_df[valid_cols].iterrows()):
        for col_idx, value in enumerate(row):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                sheet.write(row_idx + 1, col_idx, value, number_format)
            else:
                sheet.write(row_idx + 1, col_idx, str(value), data_format)


def _write_graphs_sheet(sheet, run, workbook):
    """Write embedded graphs to sheet."""
    if not run.steps:
        sheet.write(0, 0, "No data for graphs")
        return

    # 1. Time Series
    compliance_series = [calculate_compliance(step.agents) for step in run.steps]
    price_series = [step.market.price for step in run.steps]

    sheet.write(0, 0, "Compliance Over Time")
    sheet.insert_image(
        1,
        0,
        "compliance.png",
        {
            "image_data": _fig_to_bytes(
                plot_time_series(compliance_series, "Compliance", "green")
            )
        },
    )

    sheet.write(0, 8, "Price Over Time")
    sheet.insert_image(
        1,
        8,
        "price.png",
        {
            "image_data": _fig_to_bytes(
                plot_time_series(price_series, "Price ($)", "blue")
            )
        },
    )

    # 2. Snapshot Graphs (Last Step)
    if run.steps[-1].agents:
        agents_df = pd.DataFrame([a.model_dump() for a in run.steps[-1].agents])

        # Row offset for next set of graphs
        row_offset = 25

        # Plot 1: Scatter (Reported vs Used)
        # Check if columns exist (using string literals for safety if keys changed, dynamic is better but risky for logic)
        if (
            ColumnNames.USED_COMPUTE in agents_df.columns
            and ColumnNames.REPORTED_COMPUTE in agents_df.columns
        ):
            sheet.write(row_offset, 0, "True vs Reported Compute (Last Step)")
            fig, ax = plot_scatter(
                agents_df,
                ColumnNames.REPORTED_COMPUTE,
                ColumnNames.USED_COMPUTE,
                "True vs Reported Compute",
                "Reported",
                "True",
                color_logic="compliance",
            )
            # Add y=x line
            max_val = max(
                agents_df[ColumnNames.USED_COMPUTE].max(),
                agents_df[ColumnNames.REPORTED_COMPUTE].max(),
            )
            ax.plot([0, max_val], [0, max_val], "k--", alpha=0.5)
            ax.legend()
            sheet.insert_image(
                row_offset + 1, 0, "scatter.png", {"image_data": _fig_to_bytes(fig)}
            )

        # Plot 2: Deterrence Frontier
        sheet.write(row_offset, 8, "Deterrence Frontier")
        fig, _ = plot_deterrence_frontier(agents_df)
        sheet.insert_image(
            row_offset + 1, 8, "deterrence.png", {"image_data": _fig_to_bytes(fig)}
        )

        # Plot 3: Payoff Distribution
        row_offset += 25
        sheet.write(row_offset, 0, "Payoff Analysis")
        fig, _ = plot_payoff_distribution(agents_df)
        sheet.insert_image(
            row_offset + 1, 0, "payoff.png", {"image_data": _fig_to_bytes(fig)}
        )


def _fig_to_bytes(fig) -> io.BytesIO:
    """Convert matplotlib figure to bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    return buf
