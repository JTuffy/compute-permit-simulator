"""Root entry point for the Solara application.

Run with:
    uv run solara run app.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path to ensure imports work if run directly
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.append(str(src_path))

from compute_permit_sim.vis.page import Page  # noqa: E402

# ---------------------------------------------------------------------------
# Asyncio noise suppression — Python 3.13 + Solara 1.57 compatibility
#
# On Python 3.13, asyncio is stricter about Future state transitions.
# Solara's TaskAsyncio (tasks.py:347/365/388) schedules
#   call_event_loop.call_soon_threadsafe(future.set_exception, e)
# after the task has already been cancelled, raising InvalidStateError inside
# the event loop's callback dispatcher.  This is purely cosmetic — the task
# actually completed successfully — but asyncio prints it as an unhandled
# exception in callback.
#
# Solara creates a fresh event loop per virtual kernel context, so we can't
# target a specific loop instance at startup.  Patching call_exception_handler
# at the BaseEventLoop class level silences it on every loop, including the
# per-session kernel loops where the callbacks actually fire.
#
# TODO: remove once Solara fixes upstream (track: solara-ui/solara#<issue>).
# ---------------------------------------------------------------------------

_orig_call_exception_handler = asyncio.BaseEventLoop.call_exception_handler


def _suppress_solara_py313_noise(self: asyncio.BaseEventLoop, context: dict) -> None:
    exc = context.get("exception")
    if isinstance(exc, asyncio.InvalidStateError):
        return  # known race in Solara's use_task on py3.13 — harmless, skip
    _orig_call_exception_handler(self, context)


asyncio.BaseEventLoop.call_exception_handler = _suppress_solara_py313_noise  # type: ignore[method-assign]


# Expose Page for Solara
__all__ = ["Page"]
