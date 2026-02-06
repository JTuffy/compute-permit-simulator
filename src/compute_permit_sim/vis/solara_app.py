"""Main entry point for the Solara application.
Logic is now distributed across `vis/panels`, `vis/components`, and `vis/layout`.
"""

import logging

# --- Logging Configuration ---
# Force configuration of the library logger to ensure we capture output
logger = logging.getLogger("compute_permit_sim")
logger.setLevel(logging.INFO)
# Clear existing handlers to avoid duplicates
if logger.handlers:
    logger.handlers.clear()

file_handler = logging.FileHandler("outputs/simulation.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# The Page component is the root of the app
# Solara will automatically render this when running `solara run solara_app.py`
from compute_permit_sim.vis.layout.main import Page
