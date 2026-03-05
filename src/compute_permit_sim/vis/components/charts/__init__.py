"""Chart components — step-level and sim-level, organized by scope."""

from compute_permit_sim.vis.components.charts.base import (
    PlotConfig,
    apply_standard_styling,
    validate_dataframe,
)
from compute_permit_sim.vis.components.charts.deterrence import (
    AuditSourceBreakdownStepPlot,
)
from compute_permit_sim.vis.components.charts.expandable import ExpandableChart
from compute_permit_sim.vis.components.charts.longitudinal import (
    # Sim-level aggregates (RunGraphs row 2)
    SimAuditSourcePlot,
    SimAuditTargetingPlot,
    SimComplianceDistributionPlot,
    SimRiskScatterPlot,
)
from compute_permit_sim.vis.components.charts.scatter import (
    AuditSourcePlot,
    ComplianceDistributionPlot,
    QuantitativeScatterPlot,
)

__all__ = [
    # Base utilities
    "PlotConfig",
    "validate_dataframe",
    "apply_standard_styling",
    # UX
    "ExpandableChart",
    # Step-level charts
    "QuantitativeScatterPlot",
    "ComplianceDistributionPlot",
    "AuditSourcePlot",
    "AuditSourceBreakdownStepPlot",
    # Sim-level aggregates
    "SimRiskScatterPlot",
    "SimAuditTargetingPlot",
    "SimComplianceDistributionPlot",
    "SimAuditSourcePlot",
]
