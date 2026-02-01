"""Root entry point for the Solara application.

Run with:
    uv run solara run app.py
"""

import sys
from pathlib import Path

# Add src to path to ensure imports work if run directly
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.append(str(src_path))

from compute_permit_sim.vis.solara_app import Page  # noqa: E402

# Expose Page for Solara
__all__ = ["Page"]
