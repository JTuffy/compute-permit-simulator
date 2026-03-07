"""Logging configuration for the Compute Permit Simulator.

Called once at application startup from ``vis/page.py``. Configures the root
``compute_permit_sim`` logger with a timestamped stream handler.

Import this module before any other ``compute_permit_sim`` imports to ensure
consistent formatting across all submodules.
"""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the compute_permit_sim logger with a stream handler.

    Safe to call multiple times — no-ops after first call (handler guard).
    """
    logger = logging.getLogger("compute_permit_sim")
    logger.setLevel(level)

    # Guard against duplicate handlers on Solara hot-reload
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
