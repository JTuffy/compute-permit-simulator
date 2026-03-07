"""Singleton SimulationEngine instance."""

from compute_permit_sim.vis.simulation import SimulationEngine
from compute_permit_sim.vis.state.config import ui_config
from compute_permit_sim.vis.state.history import session_history

engine = SimulationEngine(ui_config, session_history)
