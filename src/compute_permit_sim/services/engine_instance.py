"""Singleton instance of the SimulationEngine.

Separated from simulation.py to avoid circular imports with vis.state modules.
"""

from compute_permit_sim.services.simulation import SimulationEngine
from compute_permit_sim.vis.state.active import active_sim
from compute_permit_sim.vis.state.config import ui_config
from compute_permit_sim.vis.state.history import session_history

# Singleton instance with default state modules injected
engine = SimulationEngine(ui_config, active_sim, session_history)
