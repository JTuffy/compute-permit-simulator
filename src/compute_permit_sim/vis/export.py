"""Export functionality for simulation runs (Excel and CSV).

Exports run data to:
1. Excel with multiple sheets (Config, Summary, [Per Seed / Trajectory / Sweep], Graphs)
2. CSV — summary row per run, or detailed step×agent rows for research.

Public API
----------
Basic runs:
    export_run_to_excel        — Excel workbook with charts
    export_run_summary_to_csv  — one summary row (matches MC/sweep shape)
    export_run_steps_to_csv    — step×agent rows for detailed analysis

Monte Carlo:
    export_monte_carlo_to_excel     — Excel with Config/Summary/Per Seed/Trajectory/Graphs
    export_monte_carlo_to_csv       — one summary row per scenario
    export_mc_per_seed_to_csv       — one row per seed (requires store_raw=True)
    export_mc_trajectory_to_csv     — per-step compliance mean/std
    export_monte_carlo_to_latex     — LaTeX tabular

Sweep:
    export_sweep_to_excel  — Excel with Config/Sweep/Graphs
    export_sweep_to_csv    — one row per parameter value

Grid Sweep (2D heatmap):
    export_grid_sweep_to_csv    — long-format CSV, one row per grid cell
    export_grid_sweep_to_excel  — Excel with Config/Grid pivot/Heatmap image
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
    GridSweepResult,
    MonteCarloResult,
    SweepResult,
)
from compute_permit_sim.schemas.batch import (
    MetricStats as _MetricStats,
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


def export_run_summary_to_csv(run, output_path: str | None = None) -> "str | bytes":
    """Export a summary of a single simulation run as a one-row CSV.

    Shape matches MC/sweep summary exports: one row, all key metrics as columns.
    Suitable for concatenating across many runs for batch comparison.

    Args:
        run: The SimulationRun to summarise.
        output_path: ``None`` = auto-generate path, ``""`` = return bytes.

    Returns:
        str (path) if written to file, bytes if output_path was ``""``.
    """
    metrics = run.metrics
    row: dict = {
        "run_id": run.id,
        "scenario": run.config.name if run.config else "",
        "seed": run.config.seed if run.config else None,
        "steps": len(run.steps),
        "n_agents": run.config.n_agents if run.config else None,
    }
    if metrics:
        for field_name in RunMetrics.model_fields:
            row[field_name] = getattr(metrics, field_name)

    df = pd.DataFrame([row])
    if output_path == "":
        return df.to_csv(index=False).encode("utf-8")
    if output_path is None:
        os.makedirs("outputs", exist_ok=True)
        fname = run.sim_id if run.sim_id else run.id
        output_path = f"outputs/simulation_run_{fname}_summary.csv"
    df.to_csv(output_path, index=False)
    return output_path


def export_run_steps_to_csv(run, output_path: str | None = None) -> "str | bytes":
    """Export step×agent rows — one row per agent per simulation step.

    Detailed research export; use ``export_run_summary_to_csv`` for
    one-click results comparison across runs.

    Args:
        run: The SimulationRun to export.
        output_path: ``None`` = auto-generate path, ``""`` = return bytes.

    Returns:
        str (path) if written to file, bytes if output_path was ``""``.
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
        output_path = f"outputs/simulation_run_{fname}_steps.csv"
    df.to_csv(output_path, index=False)
    return output_path


# Keep old name as an alias for any callers that predate the rename.
export_run_to_csv = export_run_steps_to_csv


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
            _BCN.COMPLIANT_AUDIT_FRACTION_MEAN: r.compliant_audit_fraction.mean,
            _BCN.COMPLIANT_AUDIT_FRACTION_STD: r.compliant_audit_fraction.std,
            _BCN.DETECTION_RATE_GIVEN_AUDIT_MEAN: r.detection_rate_given_audit.mean,
            _BCN.DETECTION_RATE_GIVEN_AUDIT_STD: r.detection_rate_given_audit.std,
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
            _BCN.COMPLIANT_AUDIT_FRACTION_MEAN: s.compliant_audit_fraction,
            _BCN.DETECTION_RATE_GIVEN_AUDIT_MEAN: s.detection_rate_given_audit,
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
            _BCN.COMPLIANT_AUDIT_FRACTION_MEAN: pt.result.compliant_audit_fraction.mean,
            _BCN.DETECTION_RATE_GIVEN_AUDIT_MEAN: pt.result.detection_rate_given_audit.mean,
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


def export_monte_carlo_to_excel(
    result: MonteCarloResult,
    output_path: str | None = None,
) -> "str | bytes":
    """Export a MonteCarloResult to a formatted Excel workbook.

    Sheets:
      ``Config``      — base scenario configuration used for the run
      ``Summary``     — one row of aggregate statistics
      ``Per Seed``    — one row per seed (if ``raw_seeds`` populated)
      ``Trajectory``  — per-step compliance mean/std from ``step_compliance``
      ``Graphs``      — embedded matplotlib: compliance trajectory + distribution

    Args:
        result: The ``MonteCarloResult`` to export.
        output_path: ``None`` = auto-generate path, ``""`` = return bytes.
    """
    return_bytes = output_path == ""
    output: io.BytesIO | str
    if return_bytes:
        output = io.BytesIO()
    elif output_path is None:
        os.makedirs("outputs", exist_ok=True)
        safe = result.scenario_name.lower().replace(" ", "_")
        output_path = f"outputs/mc_{safe}.xlsx"
        output = output_path
    else:
        output = output_path

    workbook = xlsxwriter.Workbook(output)
    header_fmt = workbook.add_format(
        {"bold": True, "bg_color": "#2196F3", "font_color": "white", "border": 1}
    )
    data_fmt = workbook.add_format({"border": 1})
    num_fmt = workbook.add_format({"border": 1, "num_format": "0.0000"})
    pct_fmt = workbook.add_format({"border": 1, "num_format": "0.0%"})

    try:
        # === Config sheet ===
        if result.config is not None:
            cfg_sheet = workbook.add_worksheet("Config")
            _write_config_sheet(cfg_sheet, result.config, header_fmt, data_fmt)

        # === Summary sheet ===
        summary_sheet = workbook.add_worksheet("Summary")
        summary_sheet.set_column("A:A", 32)
        summary_sheet.set_column("B:C", 16)
        row = 0
        summary_sheet.write(row, 0, "Metric", header_fmt)
        summary_sheet.write(row, 1, "Mean", header_fmt)
        summary_sheet.write(row, 2, "Std", header_fmt)
        row += 1
        _mc_summary_rows = [
            ("Scenario", result.scenario_name, ""),
            ("N Runs", result.n_runs, ""),
            ("Failed Seeds", len(result.failed_seeds), ""),
            ("Avg Compliance", result.avg_compliance.mean, result.avg_compliance.std),
            (
                "Final Compliance",
                result.final_compliance.mean,
                result.final_compliance.std,
            ),
            ("P10 Compliance", result.p10_compliance, ""),
            ("P90 Compliance", result.p90_compliance, ""),
            ("% Full Compliance", result.pct_runs_full_compliance, ""),
            ("Avg Price (M$)", result.avg_price.mean, result.avg_price.std),
            (
                "Avg Net Payoff (M$)",
                result.avg_net_payoff.mean,
                result.avg_net_payoff.std,
            ),
            (
                "Payoff Compliant (M$)",
                result.payoff_compliant.mean,
                result.payoff_compliant.std,
            ),
            (
                "Payoff Violator (M$)",
                result.payoff_violator.mean,
                result.payoff_violator.std,
            ),
            ("Audit Rate", result.audit_rate.mean, result.audit_rate.std),
            (
                "Compliant Audit Fraction",
                result.compliant_audit_fraction.mean,
                result.compliant_audit_fraction.std,
            ),
            (
                "Detection Rate (given audit)",
                result.detection_rate_given_audit.mean,
                result.detection_rate_given_audit.std,
            ),
        ]
        for label, mean_val, std_val in _mc_summary_rows:
            is_pct = (
                isinstance(mean_val, float)
                and "rate" in label.lower()
                or "compliance" in label.lower()
            )
            fmt = (
                pct_fmt
                if is_pct and isinstance(mean_val, float)
                else num_fmt
                if isinstance(mean_val, float)
                else data_fmt
            )
            std_fmt = (
                pct_fmt
                if is_pct and isinstance(std_val, float)
                else num_fmt
                if isinstance(std_val, float)
                else data_fmt
            )
            summary_sheet.write(row, 0, label, data_fmt)
            summary_sheet.write(row, 1, mean_val, fmt)
            if std_val != "":
                summary_sheet.write(row, 2, std_val, std_fmt)
            row += 1

        # === Per Seed sheet ===
        if result.raw_seeds:
            seed_sheet = workbook.add_worksheet("Per Seed")
            seed_headers = [
                "Seed",
                "Avg Compliance",
                "Final Compliance",
                "Avg Price",
                "Avg Net Payoff",
                "Payoff Compliant",
                "Payoff Violator",
                "Audit Rate",
                "Compliant Audit Fraction",
                "Detection Rate (given audit)",
            ]
            for col, h in enumerate(seed_headers):
                seed_sheet.write(0, col, h, header_fmt)
                seed_sheet.set_column(col, col, 16)
            for r_idx, s in enumerate(result.raw_seeds):
                vals = [
                    s.seed,
                    s.avg_compliance,
                    s.final_compliance,
                    s.avg_price,
                    s.avg_net_payoff,
                    s.avg_payoff_compliant,
                    s.avg_payoff_violator,
                    s.audit_rate,
                    s.compliant_audit_fraction,
                    s.detection_rate_given_audit,
                ]
                for col, v in enumerate(vals):
                    seed_sheet.write(
                        r_idx + 1, col, v, num_fmt if isinstance(v, float) else data_fmt
                    )

        # === Trajectory sheet ===
        if result.step_compliance:
            traj_sheet = workbook.add_worksheet("Trajectory")
            traj_headers = [
                "Step",
                "Compliance Mean",
                "Compliance Std",
                "Violators Mean",
                "Violators Std",
            ]
            for col, h in enumerate(traj_headers):
                traj_sheet.write(0, col, h, header_fmt)
                traj_sheet.set_column(col, col, 16)
            for step_i, (sc, sv) in enumerate(
                zip(result.step_compliance, result.step_n_violators)
            ):
                traj_sheet.write(step_i + 1, 0, step_i + 1, data_fmt)
                traj_sheet.write(step_i + 1, 1, sc.mean, num_fmt)
                traj_sheet.write(step_i + 1, 2, sc.std, num_fmt)
                traj_sheet.write(step_i + 1, 3, sv.mean, num_fmt)
                traj_sheet.write(step_i + 1, 4, sv.std, num_fmt)

        # === Graphs sheet ===
        graphs_sheet = workbook.add_worksheet("Graphs")
        _write_mc_graphs_sheet(graphs_sheet, result, workbook)

    finally:
        workbook.close()

    if return_bytes:
        assert isinstance(output, io.BytesIO)
        output.seek(0)
        return output.read()
    assert output_path is not None
    return output_path


def export_sweep_to_excel(
    result: SweepResult,
    output_path: str | None = None,
) -> "str | bytes":
    """Export a SweepResult to a formatted Excel workbook.

    Sheets:
      ``Config``  — base scenario configuration used for the run
      ``Sweep``   — one row per parameter value with aggregate stats
      ``Graphs``  — embedded matplotlib: compliance vs param + audit plot

    Args:
        result: The ``SweepResult`` to export.
        output_path: ``None`` = auto-generate path, ``""`` = return bytes.
    """
    return_bytes = output_path == ""
    output: io.BytesIO | str
    if return_bytes:
        output = io.BytesIO()
    elif output_path is None:
        os.makedirs("outputs", exist_ok=True)
        safe_s = result.scenario_name.lower().replace(" ", "_")
        safe_p = result.param_path.replace(".", "_")
        output_path = f"outputs/sweep_{safe_s}_{safe_p}.xlsx"
        output = output_path
    else:
        output = output_path

    workbook = xlsxwriter.Workbook(output)
    header_fmt = workbook.add_format(
        {"bold": True, "bg_color": "#2196F3", "font_color": "white", "border": 1}
    )
    data_fmt = workbook.add_format({"border": 1})
    num_fmt = workbook.add_format({"border": 1, "num_format": "0.0000"})

    try:
        # === Config sheet ===
        if result.config is not None:
            cfg_sheet = workbook.add_worksheet("Config")
            _write_config_sheet(cfg_sheet, result.config, header_fmt, data_fmt)

        # === Sweep sheet ===
        sweep_sheet = workbook.add_worksheet("Sweep")
        sweep_headers = [
            result.param_label or result.param_path,
            "N Runs",
            "Avg Compliance",
            "Compliance Std",
            "P10 Compliance",
            "P90 Compliance",
            "Avg Price",
            "Avg Net Payoff",
            "Audit Rate",
            "Detection Rate (given audit)",
        ]
        for col, h in enumerate(sweep_headers):
            sweep_sheet.write(0, col, h, header_fmt)
            sweep_sheet.set_column(col, col, 16)

        for row_i, pt in enumerate(result.points):
            vals = [
                pt.param_value,
                pt.result.n_runs,
                pt.result.avg_compliance.mean,
                pt.result.avg_compliance.std,
                pt.result.p10_compliance,
                pt.result.p90_compliance,
                pt.result.avg_price.mean,
                pt.result.avg_net_payoff.mean,
                pt.result.audit_rate.mean,
                pt.result.detection_rate_given_audit.mean,
            ]
            for col, v in enumerate(vals):
                sweep_sheet.write(
                    row_i + 1, col, v, num_fmt if isinstance(v, float) else data_fmt
                )

        # === Graphs sheet ===
        graphs_sheet = workbook.add_worksheet("Graphs")
        _write_sweep_graphs_sheet(graphs_sheet, result, workbook)

    finally:
        workbook.close()

    if return_bytes:
        assert isinstance(output, io.BytesIO)
        output.seek(0)
        return output.read()
    assert output_path is not None
    return output_path


# ---------------------------------------------------------------------------
# Internal graph helpers for MC and Sweep Excel sheets
# ---------------------------------------------------------------------------


def _write_mc_graphs_sheet(sheet, result: MonteCarloResult, workbook) -> None:
    """Embed compliance trajectory and distribution charts into the Graphs sheet."""
    import matplotlib

    matplotlib.use("Agg")  # ensure non-interactive backend in export context
    import matplotlib.pyplot as plt

    if not result.step_compliance:
        sheet.write(0, 0, "No trajectory data available")
        return

    # Chart 1: Compliance trajectory with ±1 SD band
    steps_x = list(range(1, len(result.step_compliance) + 1))
    means = [s.mean for s in result.step_compliance]
    stds = [s.std for s in result.step_compliance]
    lower = [max(0.0, m - s) for m, s in zip(means, stds)]
    upper = [min(1.0, m + s) for m, s in zip(means, stds)]

    fig1, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(steps_x, means, color="#1976D2", linewidth=2, label="Mean")
    ax1.fill_between(steps_x, lower, upper, alpha=0.2, color="#1976D2", label="±1 SD")
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Compliance Rate")
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_title(f"Compliance Trajectory — {result.scenario_name}")
    ax1.legend(fontsize=8)
    fig1.tight_layout()

    sheet.write(0, 0, "Compliance Trajectory (Mean ± 1 SD)")
    sheet.insert_image(
        1, 0, "compliance_trajectory.png", {"image_data": _fig_to_bytes(fig1)}
    )
    plt.close(fig1)

    # Chart 2: Final compliance distribution across seeds
    if result.raw_seeds:
        compliances = [s.final_compliance for s in result.raw_seeds]
        fig2, ax2 = plt.subplots(figsize=(5, 4))
        ax2.hist(
            compliances,
            bins=min(15, len(compliances)),
            color="#43A047",
            edgecolor="white",
            alpha=0.85,
        )
        ax2.set_xlabel("Final Compliance Rate")
        ax2.set_ylabel("Count")
        ax2.set_title("Seed Distribution: Final Compliance")
        fig2.tight_layout()
        sheet.write(0, 9, "Final Compliance Distribution (Seeds)")
        sheet.insert_image(
            1, 9, "compliance_dist.png", {"image_data": _fig_to_bytes(fig2)}
        )
        plt.close(fig2)


def _write_sweep_graphs_sheet(sheet, result: SweepResult, workbook) -> None:
    """Embed compliance vs parameter chart and audit rate chart into the Graphs sheet."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not result.points:
        sheet.write(0, 0, "No sweep data available")
        return

    param_values = [pt.param_value for pt in result.points]
    comp_means = [pt.result.avg_compliance.mean for pt in result.points]
    comp_stds = [pt.result.avg_compliance.std for pt in result.points]
    lower = [max(0.0, m - s) for m, s in zip(comp_means, comp_stds)]
    upper = [min(1.0, m + s) for m, s in zip(comp_means, comp_stds)]
    audit_means = [pt.result.audit_rate.mean for pt in result.points]

    param_label = result.param_label or result.param_path

    # Chart 1: Compliance vs param with shaded CI band
    fig1, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(
        param_values, comp_means, color="#1976D2", linewidth=2, marker="o", markersize=5
    )
    ax1.fill_between(param_values, lower, upper, alpha=0.2, color="#1976D2")
    ax1.set_xlabel(param_label)
    ax1.set_ylabel("Avg Compliance Rate")
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_title(f"Compliance vs {param_label}")
    fig1.tight_layout()
    sheet.write(0, 0, f"Avg Compliance vs {param_label} (Mean ± 1 SD)")
    sheet.insert_image(
        1, 0, "sweep_compliance.png", {"image_data": _fig_to_bytes(fig1)}
    )
    plt.close(fig1)

    # Chart 2: Audit rate vs param
    fig2, ax2 = plt.subplots(figsize=(5, 4))
    ax2.plot(
        param_values,
        audit_means,
        color="#E53935",
        linewidth=2,
        marker="o",
        markersize=5,
    )
    ax2.set_xlabel(param_label)
    ax2.set_ylabel("Avg Audit Rate")
    ax2.set_title(f"Audit Rate vs {param_label}")
    fig2.tight_layout()
    sheet.write(0, 9, f"Audit Rate vs {param_label}")
    sheet.insert_image(1, 9, "sweep_audit.png", {"image_data": _fig_to_bytes(fig2)})
    plt.close(fig2)


# =============================================================================
# Grid Sweep (2D Heatmap) Exports
# =============================================================================


def export_grid_sweep_to_csv(
    result: GridSweepResult,
    output_path: str | None = None,
) -> "str | bytes":
    """Export a GridSweepResult to long-format CSV with one row per grid cell.

    Columns: scenario, param_x_path, param_x_value, param_y_path,
    param_y_value, n_runs, compliance.

    Args:
        result: A ``GridSweepResult`` instance.
        output_path: ``None`` = auto-generate, ``""`` = return bytes.
    """
    rows = [
        {
            _BCN.SCENARIO: result.scenario_name,
            _BCN.PARAM_X_PATH: result.param_x_path,
            _BCN.PARAM_X_VALUE: x,
            _BCN.PARAM_Y_PATH: result.param_y_path,
            _BCN.PARAM_Y_VALUE: y,
            _BCN.N_RUNS: result.n_runs,
            _BCN.COMPLIANCE_RATE: result.grid[y_idx][x_idx],
        }
        for y_idx, y in enumerate(result.y_values)
        for x_idx, x in enumerate(result.x_values)
    ]

    df = _pd.DataFrame(rows)
    if output_path == "":
        return df.to_csv(index=False).encode("utf-8")
    if output_path is None:
        _os.makedirs("outputs", exist_ok=True)
        safe_s = result.scenario_name.lower().replace(" ", "_")
        safe_x = result.param_x_path.replace(".", "_")
        safe_y = result.param_y_path.replace(".", "_")
        output_path = f"outputs/grid_{safe_s}_{safe_x}_x_{safe_y}.csv"
    df.to_csv(output_path, index=False)
    return output_path


def export_grid_sweep_to_excel(
    result: GridSweepResult,
    output_path: str | None = None,
) -> "str | bytes":
    """Export a GridSweepResult to a formatted Excel workbook.

    Sheets:
      ``Config``   — base scenario configuration
      ``Grid``     — pivot table: rows=y_values, cols=x_values, cells=compliance%
      ``Heatmap``  — embedded PNG of the compliance heatmap

    Args:
        result: A ``GridSweepResult`` instance.
        output_path: ``None`` = auto-generate, ``""`` = return bytes.
    """
    import io as _io

    import xlsxwriter as _xlsxwriter

    from compute_permit_sim.vis.plotting import plot_sweep_heatmap

    return_bytes = output_path == ""
    output: _io.BytesIO | str
    if return_bytes:
        output = _io.BytesIO()
    elif output_path is None:
        _os.makedirs("outputs", exist_ok=True)
        safe_s = result.scenario_name.lower().replace(" ", "_")
        safe_x = result.param_x_path.replace(".", "_")
        safe_y = result.param_y_path.replace(".", "_")
        output_path = f"outputs/grid_{safe_s}_{safe_x}_x_{safe_y}.xlsx"
        output = output_path
    else:
        output = output_path

    workbook = _xlsxwriter.Workbook(output)
    header_fmt = workbook.add_format(
        {"bold": True, "bg_color": "#2196F3", "font_color": "white", "border": 1}
    )
    data_fmt = workbook.add_format({"border": 1})
    pct_fmt = workbook.add_format({"border": 1, "num_format": "0.0%"})

    try:
        # === Config sheet ===
        if result.config is not None:
            cfg_sheet = workbook.add_worksheet("Config")
            _write_config_sheet(cfg_sheet, result.config, header_fmt, data_fmt)

        # === Grid (pivot) sheet ===
        grid_sheet = workbook.add_worksheet("Grid")
        grid_sheet.set_column("A:A", 20)
        grid_sheet.write(
            0,
            0,
            f"{result.param_x_label} \u2192 / {result.param_y_label} \u2193",
            header_fmt,
        )
        for x_idx, x in enumerate(result.x_values):
            grid_sheet.write(0, x_idx + 1, x, header_fmt)
        for y_idx, y in enumerate(result.y_values):
            grid_sheet.write(y_idx + 1, 0, y, data_fmt)
            for x_idx, compliance in enumerate(result.grid[y_idx]):
                grid_sheet.write(y_idx + 1, x_idx + 1, compliance, pct_fmt)

        # === Heatmap sheet ===
        heatmap_sheet = workbook.add_worksheet("Heatmap")
        fig = plot_sweep_heatmap(
            compliance_grid=result.grid,
            x_values=result.x_values,
            y_values=result.y_values,
            x_param_label=result.param_x_label,
            y_param_label=result.param_y_label,
            title=f"Compliance Heatmap \u2014 {result.scenario_name}",
        )
        heatmap_sheet.insert_image(
            0, 0, "heatmap.png", {"image_data": _fig_to_bytes(fig)}
        )

    finally:
        workbook.close()

    if return_bytes:
        assert isinstance(output, _io.BytesIO)
        output.seek(0)
        return output.read()

    assert output_path is not None
    return output_path
