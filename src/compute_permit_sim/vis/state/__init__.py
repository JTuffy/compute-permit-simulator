"""State management package for visualization infrastructure.

This package provides modular state management split by concern:
- config: UI-bound configuration parameters
- active: Live simulation state
- history: Session run history
- engine: Singleton SimulationEngine instance
"""

from compute_permit_sim.vis.state.active import ActiveSimulation, active_sim
from compute_permit_sim.vis.state.config import UIConfig, ui_config
from compute_permit_sim.vis.state.engine import engine
from compute_permit_sim.vis.state.history import SessionHistory, session_history

__all__ = [
    "UIConfig",
    "ui_config",
    "ActiveSimulation",
    "active_sim",
    "SessionHistory",
    "session_history",
    "engine",
]
