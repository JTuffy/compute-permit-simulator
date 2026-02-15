"""Singleton SimulationEngine instance.

Wires UI state modules (config, active, history) into the engine.
Lives in vis/state because it depends on UI state objects.
"""

from compute_permit_sim.vis.simulation import SimulationEngine
from compute_permit_sim.vis.state.active import active_sim
from compute_permit_sim.vis.state.config import ui_config
from compute_permit_sim.vis.state.history import session_history

# Singleton instance with default state modules injected
engine = SimulationEngine(ui_config, active_sim, session_history)
