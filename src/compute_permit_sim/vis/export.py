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
from compute_permit_sim.schemas.batch import (
    BatchColumnNames as _BCN,
)
from compute_permit_sim.schemas.batch import (
    MetricStats as _MetricStats,
)
from compute_permit_sim.schemas.batch import (
    MonteCarloResult,
    SweepResult,
)
from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.services.metrics import calculate_compliance
from compute_permit_sim.vis.plotting import (
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
    output: io.BytesIO | str

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
        assert isinstance(output, io.BytesIO)
        output.seek(0)
        return output.read()

    assert output_path is not None
    return output_path


def export_run_to_csv(run, output_path: str | None = None) -> str | bytes:
    """Export a simulation run to a CSV file with step-wise agent data.

    Each row represents one agent at one simulation step.
    Config parameters are NOT included — use the Excel export for full config.

    Args:
        run: The simulation run to export.
        output_path: File path to write to (None=auto, ""=bytes).

    Returns:
        str (path) if written to file, bytes if output_path was "".
    """
    rows = []
    for step_res in run.steps:
        market_data = {
            "run_id": run.id,
            "step": step_res.step,
            "market_price": step_res.market.price,
            "market_supply": step_res.market.supply,
        }
        for agent in step_res.agents:
            row = market_data.copy()
            row.update({f"agent_{k}": v for k, v in agent.model_dump().items()})
            rows.append(row)

    df = pd.DataFrame(rows) if rows else pd.DataFrame()

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
                extra = field_info.json_schema_extra
                default_title = name.replace("_", " ").title()
                section_title: str = (
                    str(extra.get("ui_group", default_title))
                    if isinstance(extra, dict)
                    else default_title
                )

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
            ColumnNames.USED_TRAINING_FLOPS in agents_df.columns
            and ColumnNames.REPORTED_TRAINING_FLOPS in agents_df.columns
        ):
            sheet.write(row_offset, 0, "True vs Reported FLOPs (Last Step)")
            fig, ax = plot_scatter(
                agents_df,
                ColumnNames.REPORTED_TRAINING_FLOPS,
                ColumnNames.USED_TRAINING_FLOPS,
                "True vs Reported FLOPs",
                "Reported",
                "True",
                color_logic="compliance",
            )
            # Add y=x line
            max_val = max(
                agents_df[ColumnNames.USED_TRAINING_FLOPS].max(),
                agents_df[ColumnNames.REPORTED_TRAINING_FLOPS].max(),
            )
            ax.plot(
                [0, max_val],
                [0, max_val],
                "k--",
                alpha=0.5,
                label="y=x (perfect reporting)",
            )
            ax.legend()
            sheet.insert_image(
                row_offset + 1, 0, "scatter.png", {"image_data": _fig_to_bytes(fig)}
            )


def _fig_to_bytes(fig) -> io.BytesIO:
    """Convert matplotlib figure to bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    return buf


# =============================================================================
# Batch / Monte Carlo Exports
# =============================================================================

_os = os
_pd = pd


def export_monte_carlo_to_csv(
    results: list[MonteCarloResult],
    output_path: str | None = None,
) -> "str | bytes":
    """Export a list of MonteCarloResult objects to a summary CSV.

    One row per scenario. Columns use :class:`~BatchColumnNames` constants.

    Args:
        results: List of ``MonteCarloResult`` instances.
        output_path: ``None`` = auto-generate path, ``""`` = return bytes.
    """
    rows = [
        {
            _BCN.SCENARIO: r.scenario_name,
            _BCN.N_RUNS: r.n_runs,
            _BCN.AVG_COMPLIANCE_MEAN: r.avg_compliance.mean,
            _BCN.AVG_COMPLIANCE_STD: r.avg_compliance.std,
            _BCN.FINAL_COMPLIANCE_MEAN: r.final_compliance.mean,
            "final_compliance_std": r.final_compliance.std,
            _BCN.P10_COMPLIANCE: r.p10_compliance,
            _BCN.P90_COMPLIANCE: r.p90_compliance,
            _BCN.PCT_RUNS_FULL_COMPLIANCE: r.pct_runs_full_compliance,
            _BCN.AVG_PRICE_MEAN: r.avg_price.mean,
            _BCN.AVG_PRICE_STD: r.avg_price.std,
            _BCN.AVG_NET_PAYOFF_MEAN: r.avg_net_payoff.mean,
            _BCN.AVG_NET_PAYOFF_STD: r.avg_net_payoff.std,
            _BCN.PAYOFF_COMPLIANT_MEAN: r.payoff_compliant.mean,
            _BCN.PAYOFF_COMPLIANT_STD: r.payoff_compliant.std,
            _BCN.PAYOFF_VIOLATOR_MEAN: r.payoff_violator.mean,
            _BCN.PAYOFF_VIOLATOR_STD: r.payoff_violator.std,
            _BCN.AUDIT_RATE_MEAN: r.audit_rate.mean,
            _BCN.AUDIT_RATE_STD: r.audit_rate.std,
            _BCN.FALSE_POSITIVE_RATE_MEAN: r.false_positive_rate.mean,
            _BCN.FALSE_POSITIVE_RATE_STD: r.false_positive_rate.std,
            _BCN.DETECTION_RATE_MEAN: r.detection_rate.mean,
            _BCN.DETECTION_RATE_STD: r.detection_rate.std,
        }
        for r in results
    ]

    df = _pd.DataFrame(rows)
    if output_path == "":
        return df.to_csv(index=False).encode("utf-8")
    if output_path is None:
        _os.makedirs("outputs", exist_ok=True)
        output_path = "outputs/monte_carlo_summary.csv"
    df.to_csv(output_path, index=False)
    return output_path


def export_mc_per_seed_to_csv(
    result: MonteCarloResult,
    output_path: str | None = None,
) -> "str | bytes":
    """Export per-seed scalar summaries — one row per seed.

    Requires ``MonteCarloResult.raw_seeds`` to be populated
    (i.e. ``store_raw=True`` was passed to ``run_monte_carlo``).

    Args:
        result: A ``MonteCarloResult`` with ``raw_seeds`` populated.
        output_path: ``None`` = auto-generate, ``""`` = return bytes.

    Raises:
        ValueError: If ``raw_seeds`` is empty.
    """
    if not result.raw_seeds:
        raise ValueError(
            "MonteCarloResult.raw_seeds is empty. "
            "Run with store_raw=True to capture per-seed data."
        )

    rows = [
        {
            _BCN.SCENARIO: result.scenario_name,
            _BCN.SEED: s.seed,
            _BCN.AVG_COMPLIANCE_MEAN: s.avg_compliance,
            _BCN.FINAL_COMPLIANCE_MEAN: s.final_compliance,
            _BCN.AVG_PRICE_MEAN: s.avg_price,
            _BCN.AVG_NET_PAYOFF_MEAN: s.avg_net_payoff,
            _BCN.PAYOFF_COMPLIANT_MEAN: s.avg_payoff_compliant,
            _BCN.PAYOFF_VIOLATOR_MEAN: s.avg_payoff_violator,
            _BCN.AUDIT_RATE_MEAN: s.audit_rate,
            _BCN.FALSE_POSITIVE_RATE_MEAN: s.false_positive_rate,
            _BCN.DETECTION_RATE_MEAN: s.detection_rate,
        }
        for s in result.raw_seeds
    ]

    df = _pd.DataFrame(rows)
    if output_path == "":
        return df.to_csv(index=False).encode("utf-8")
    if output_path is None:
        _os.makedirs("outputs", exist_ok=True)
        safe = result.scenario_name.lower().replace(" ", "_")
        output_path = f"outputs/mc_per_seed_{safe}.csv"
    df.to_csv(output_path, index=False)
    return output_path


def export_mc_trajectory_to_csv(
    result: MonteCarloResult,
    output_path: str | None = None,
) -> "str | bytes":
    """Export per-step trajectory data in long format — one row per step.

    Columns: step, compliance_mean, compliance_std, n_violators_mean,
    n_violators_std.  Downstream tools (R, matplotlib) can use this
    directly for publication trajectory plots.

    Args:
        result: A ``MonteCarloResult`` with ``step_compliance`` populated.
        output_path: ``None`` = auto-generate, ``""`` = return bytes.
    """
    rows = [
        {
            _BCN.SCENARIO: result.scenario_name,
            _BCN.STEP: step + 1,
            _BCN.COMPLIANCE_RATE: s.mean,
            f"{_BCN.COMPLIANCE_RATE}_std": s.std,
            _BCN.N_VIOLATORS: v.mean,
            f"{_BCN.N_VIOLATORS}_std": v.std,
        }
        for step, (s, v) in enumerate(
            zip(result.step_compliance, result.step_n_violators)
        )
    ]

    df = _pd.DataFrame(rows)
    if output_path == "":
        return df.to_csv(index=False).encode("utf-8")
    if output_path is None:
        _os.makedirs("outputs", exist_ok=True)
        safe = result.scenario_name.lower().replace(" ", "_")
        output_path = f"outputs/mc_trajectory_{safe}.csv"
    df.to_csv(output_path, index=False)
    return output_path


def export_monte_carlo_to_latex(results: list[MonteCarloResult]) -> str:
    """Generate a ready-to-paste LaTeX tabular for Monte Carlo results.

    Columns: Scenario, Avg Compliance (P10–P90), Market Price,
    Net Payoff, Audit Rate, and % Full Compliance.
    Format: mean (SD) where SD > 0, plain mean if deterministic.
    """

    def _pct(s: _MetricStats) -> str:
        mean, sd = s.mean * 100, s.std * 100
        if sd < 1e-9:
            return rf"{mean:.1f}\%"
        return rf"{mean:.1f} ({sd:.1f})\%"

    def _flt(s: _MetricStats) -> str:
        mean, sd = s.mean, s.std
        if sd < 1e-9:
            return f"{mean:.2f}"
        return f"{mean:.2f} ({sd:.2f})"

    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\small",
        r"\caption{Simulation outcomes by scenario (mean with SD in parentheses; compliance range is P10--P90 across seeds).}",
        r"\label{tab:mc-results}",
        r"\begin{tabular}{lcccccc}",
        r"\toprule",
        (
            r"\textbf{Scenario} "
            r"& \textbf{Avg Compliance} "
            r"& \textbf{P10--P90 Range} "
            r"& \textbf{Price (M\$)} "
            r"& \textbf{Net Payoff (M\$)} "
            r"& \textbf{Audit Rate} "
            r"& \textbf{Full Compliance \%} \\\\"
        ),
        r"\midrule",
    ]
    for r in results:
        p10 = f"{r.p10_compliance * 100:.1f}"
        p90 = f"{r.p90_compliance * 100:.1f}"
        pct_full = f"{r.pct_runs_full_compliance * 100:.0f}\\%"
        lines.append(
            f"{r.scenario_name} "
            f"& {_pct(r.avg_compliance)} "
            f"& [{p10}\\%--{p90}\\%] "
            f"& {_flt(r.avg_price)} "
            f"& {_flt(r.avg_net_payoff)} "
            f"& {_pct(r.audit_rate)} "
            f"& {pct_full} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
        "",
        r"% Compliance: mean (SD); P10/P90 across seeds; payoffs in M$.",
    ]
    return "\n".join(lines)


def export_sweep_to_csv(
    result: SweepResult,
    output_path: str | None = None,
) -> "str | bytes":
    """Export a SweepResult to CSV with one row per sweep point.

    Args:
        result: A ``SweepResult`` instance.
        output_path: ``None`` = auto-generate, ``""`` = return bytes.
    """
    rows = [
        {
            _BCN.SCENARIO: result.scenario_name,
            _BCN.PARAM_PATH: result.param_path,
            _BCN.PARAM_VALUE: pt.param_value,
            _BCN.N_RUNS: pt.result.n_runs,
            _BCN.AVG_COMPLIANCE_MEAN: pt.result.avg_compliance.mean,
            _BCN.AVG_COMPLIANCE_STD: pt.result.avg_compliance.std,
            _BCN.P10_COMPLIANCE: pt.result.p10_compliance,
            _BCN.P90_COMPLIANCE: pt.result.p90_compliance,
            _BCN.AVG_PRICE_MEAN: pt.result.avg_price.mean,
            _BCN.AVG_PRICE_STD: pt.result.avg_price.std,
            _BCN.AVG_NET_PAYOFF_MEAN: pt.result.avg_net_payoff.mean,
            _BCN.AVG_NET_PAYOFF_STD: pt.result.avg_net_payoff.std,
            _BCN.PAYOFF_COMPLIANT_MEAN: pt.result.payoff_compliant.mean,
            _BCN.PAYOFF_VIOLATOR_MEAN: pt.result.payoff_violator.mean,
            _BCN.AUDIT_RATE_MEAN: pt.result.audit_rate.mean,
            _BCN.AUDIT_RATE_STD: pt.result.audit_rate.std,
            _BCN.FALSE_POSITIVE_RATE_MEAN: pt.result.false_positive_rate.mean,
            _BCN.DETECTION_RATE_MEAN: pt.result.detection_rate.mean,
        }
        for pt in result.points
    ]

    df = _pd.DataFrame(rows)
    if output_path == "":
        return df.to_csv(index=False).encode("utf-8")
    if output_path is None:
        _os.makedirs("outputs", exist_ok=True)
        safe_s = result.scenario_name.lower().replace(" ", "_")
        safe_p = result.param_path.replace(".", "_")
        output_path = f"outputs/sweep_{safe_s}_{safe_p}.csv"
    df.to_csv(output_path, index=False)
    return output_path
