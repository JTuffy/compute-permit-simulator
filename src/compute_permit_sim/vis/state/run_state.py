"""Generic run state reactive for all simulation modes.

Every run type (basic, Monte Carlo, sweep) transitions through the same
three phases: idle → running → ready.

The phase drives the page-level right-pane state machine in ``vis/page.py``.
Individual result panels read ``result`` directly — no intermediate state
and no multiple reactive updates on completion.

Usage:
    # Start a run
    basic_run.set(RunState[SimulationRun](phase="running"))

    # Complete
    basic_run.set(RunState[SimulationRun](phase="ready", result=run))

    # Reset (new run click auto-resets via phase="running", result=None)
"""

from __future__ import annotations

from typing import Generic, Literal, TypeVar

import solara
from pydantic import BaseModel, ConfigDict

from compute_permit_sim.schemas import SimulationRun
from compute_permit_sim.schemas.batch import (
    GridSweepResult,
    MonteCarloResult,
    SweepResult,
)

T = TypeVar("T")


class RunState(BaseModel, Generic[T]):
    """Immutable run phase + result container.

    ``phase`` controls what the right pane renders.
    ``result`` is populated atomically when phase transitions to "ready".
    """

    model_config = ConfigDict(frozen=True)

    phase: Literal["idle", "running", "ready"] = "idle"
    result: T | None = None

    @property
    def is_running(self) -> bool:
        return self.phase == "running"

    @property
    def is_ready(self) -> bool:
        return self.phase == "ready"


# ---------------------------------------------------------------------------
# Module-level singletons — imported directly by panels and page.py
# ---------------------------------------------------------------------------

#: Basic single-scenario run state
basic_run: solara.Reactive[RunState[SimulationRun]] = solara.reactive(
    RunState[SimulationRun]()
)

#: Monte Carlo batch run state
mc_run: solara.Reactive[RunState[MonteCarloResult]] = solara.reactive(
    RunState[MonteCarloResult]()
)

#: Parameter sweep batch run state
sweep_run: solara.Reactive[RunState[SweepResult]] = solara.reactive(
    RunState[SweepResult]()
)

#: 2D grid sweep batch run state
grid_run: solara.Reactive[RunState[GridSweepResult]] = solara.reactive(
    RunState[GridSweepResult]()
)
