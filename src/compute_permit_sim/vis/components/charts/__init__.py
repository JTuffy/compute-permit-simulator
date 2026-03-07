"""Chart components — step-level and aggregate, organized by scope.

All chart components accept a ``mode`` parameter (``"aggregate" | "step"``).
The same component handles both views; titles and data sources switch
automatically based on mode.
"""

from compute_permit_sim.vis.components.charts.base import (
    PlotConfig,
    apply_standard_styling,
    validate_dataframe,
)
from compute_permit_sim.vis.components.charts.deterrence import AuditTargetingPlot
from compute_permit_sim.vis.components.charts.expandable import ExpandableChart
from compute_permit_sim.vis.components.charts.scatter import (
    AuditSourcePlot,
    ComplianceDistributionPlot,
    RiskScatterPlot,
)

__all__ = [
    # Base utilities
    "PlotConfig",
    "validate_dataframe",
    "apply_standard_styling",
    # UX
    "ExpandableChart",
    # Mode-aware chart components (pass mode="step" or mode="aggregate")
    "RiskScatterPlot",
    "AuditTargetingPlot",
    "ComplianceDistributionPlot",
    "AuditSourcePlot",
]
