"""Unit tests for export service."""

import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from compute_permit_sim.schemas.config import (
    AuditConfig,
    LabConfig,
    MarketConfig,
    ScenarioConfig,
)
from compute_permit_sim.schemas.data import (
    MarketSnapshot,
    RunMetrics,
    SimulationRun,
    StepResult,
)
from compute_permit_sim.vis.export import export_run_to_csv, export_run_to_excel


@pytest.fixture
def sample_run(agent_snapshot_factory) -> SimulationRun:
    """Create a sample simulation run for testing."""
    config = ScenarioConfig(
        name="Test Run",
        steps=10,
        n_agents=5,
        market=MarketConfig(permit_cap=1000),
        audit=AuditConfig(),
        lab=LabConfig(),
    )

    steps = []
    for i in range(3):
        steps.append(
            StepResult(
                step=i + 1,
                market=MarketSnapshot(price=10.0, supply=100.0),
                agents=[
                    agent_snapshot_factory(id=1, is_compliant=True),
                    agent_snapshot_factory(id=2, is_compliant=False),
                ],
                audit=[],
            )
        )

    return SimulationRun(
        id="test_run_123",
        config=config,
        steps=steps,
        metrics=RunMetrics(
            final_compliance=0.5,
            final_price=10.0,
            deterrence_success_rate=0.5,
        ),
    )


def test_export_run_to_csv_creates_file(sample_run: SimulationRun) -> None:
    """Test that CSV export creates a file with step-wise agent data only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_export.csv"

        result_path = export_run_to_csv(sample_run, output_path=str(output_path))

        assert os.path.exists(result_path)

        df = pd.read_csv(result_path)

        # 3 steps x 2 agents = 6 rows
        assert len(df) == 6
        assert "step" in df.columns
        assert "market_price" in df.columns
        assert "agent_id" in df.columns
        # Config should NOT be in the CSV
        assert "config_name" not in df.columns
        assert df["market_price"].iloc[0] == 10.0


def test_export_run_to_excel_creates_file(sample_run: SimulationRun) -> None:
    """Test that export creates a valid Excel file with expected sheets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_export.xlsx"

        # Run export
        result_path = export_run_to_excel(sample_run, output_path=str(output_path))

        assert os.path.exists(result_path)

        # Verify sheets using pandas
        with pd.ExcelFile(result_path) as xl:
            sheet_names = xl.sheet_names

            assert "Configuration" in sheet_names
            assert "Summary" in sheet_names
            assert "Agent Details" in sheet_names
            assert "Graphs" in sheet_names

        # Verify Content - Config
        df_config = pd.read_excel(result_path, sheet_name="Configuration")
        assert not df_config.empty

        # Verify Content - Agent Details
        df_agents = pd.read_excel(result_path, sheet_name="Agent Details")
        # Header row is parsed, we expect 2 agents
        assert len(df_agents) == 2
        assert "Agent's base economic value (v_i)" in df_agents.columns


# ---------------------------------------------------------------------------
# Grid sweep export tests
# ---------------------------------------------------------------------------


def test_export_grid_sweep_to_csv_bytes() -> None:
    """CSV export returns bytes with n_x * n_y rows and expected columns."""
    from compute_permit_sim.vis.export import export_grid_sweep_to_csv
    from tests.factories import create_grid_sweep_result

    n_x, n_y = 3, 2
    result = create_grid_sweep_result(n_x=n_x, n_y=n_y)
    csv_bytes = export_grid_sweep_to_csv(result, output_path="")
    assert isinstance(csv_bytes, bytes)

    import io

    df = pd.read_csv(io.BytesIO(csv_bytes))
    assert len(df) == n_x * n_y
    required_cols = {
        "param_x_path",
        "param_x_value",
        "param_y_path",
        "param_y_value",
        "n_runs",
        "compliance_rate",
    }
    assert required_cols.issubset(set(df.columns))


def test_export_grid_sweep_to_excel_bytes() -> None:
    """Excel export returns non-empty bytes with Config, Grid, and Heatmap sheets."""
    from compute_permit_sim.vis.export import export_grid_sweep_to_excel
    from tests.factories import create_grid_sweep_result

    result = create_grid_sweep_result(n_x=2, n_y=2)
    xlsx_bytes = export_grid_sweep_to_excel(result, output_path="")
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 0

    import io

    with pd.ExcelFile(io.BytesIO(xlsx_bytes)) as xl:
        assert "Config" in xl.sheet_names
        assert "Grid" in xl.sheet_names
        assert "Heatmap" in xl.sheet_names
