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
from compute_permit_sim.vis.export import export_run_to_excel


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
