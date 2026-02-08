"""Chart components - organized by plot type for clarity and maintainability."""

from compute_permit_sim.vis.components.charts.base import (
    PlotConfig,
    apply_standard_styling,
    validate_dataframe,
)
from compute_permit_sim.vis.components.charts.deterrence import (
    AuditTargetingPlot,
    LabDecisionPlot,
)
from compute_permit_sim.vis.components.charts.payoff import (
    PayoffByStrategyPlot,
    WealthDivergencePlot,
)
from compute_permit_sim.vis.components.charts.scatter import (
    CapacityUtilizationPlot,
    CheatingGainPlot,
    QuantitativeScatterPlot,
)

__all__ = [
    # Base utilities
    "PlotConfig",
    "validate_dataframe",
    "apply_standard_styling",
    # Scatter plots
    "QuantitativeScatterPlot",
    "CheatingGainPlot",
    "CapacityUtilizationPlot",
    # Audit & Deterrence
    "AuditTargetingPlot",
    "LabDecisionPlot",
    # Payoff & Wealth
    "PayoffByStrategyPlot",
    "WealthDivergencePlot",
]
