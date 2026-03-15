"""Unified history list — shared between Simulate and Batch sidebar tabs.

Individual item components (RunHistoryItem, BatchHistoryItem) live in
``history_items.py``; this file owns only the list container.

Re-exports RunHistoryItem and BatchHistoryItem for backwards-compatibility
with any import that came directly from this module.
"""

from __future__ import annotations

import solara

from compute_permit_sim.vis.components.history_items import (  # noqa: F401 — re-export
    BatchHistoryItem,
    RunHistoryItem,
)
from compute_permit_sim.vis.state.history import session_history


@solara.component
def UnifiedHistoryList() -> None:
    """Single, uniformly styled history stream — batch results then basic runs.

    Owns the sole ``run-history-compact`` wrapper so every item type (MC, Sweep,
    basic run) receives identical CSS context. Replaces the paired
    (BatchHistoryList + RunHistoryList) pattern which caused double-nested
    ``run-history-compact`` for batch items and mismatched styling.
    """
    from compute_permit_sim.vis.state.run_state import grid_run, mc_run, sweep_run

    batch_results = session_history.batch_results.value
    run_history = session_history.run_history.value
    mc_current = mc_run.value.result
    sweep_current = sweep_run.value.result
    grid_current = grid_run.value.result

    # Use Markdown for empty state — matches RunHistoryList convention and avoids
    # alternating root container types (Column A vs Column B) which reacton rejects.
    if not batch_results and not run_history:
        solara.Markdown("_No runs yet._")
        return

    with solara.Column(classes=["run-history-compact"]):
        for result in batch_results:
            is_current = (
                (result is mc_current)
                or (result is sweep_current)
                or (result is grid_current)
            )
            BatchHistoryItem(result, is_current)
        for run in run_history:
            is_selected = (session_history.selected_run.value is not None) and (
                session_history.selected_run.value.id == run.id
            )
            RunHistoryItem(run, is_selected)
