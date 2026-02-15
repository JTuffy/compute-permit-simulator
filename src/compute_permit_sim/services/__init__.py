"""Services package — infrastructure adapters.

Modules:
 - mesa_model.py: Mesa model integration (ComputePermitModel)
 - config_manager.py: Scenario file loading/saving
 - metrics.py: Pure metric calculations
"""

from compute_permit_sim.services.mesa_model import ComputePermitModel

__all__ = ["ComputePermitModel"]
