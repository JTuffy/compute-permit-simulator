"""Shared full-panel loading spinner for simulation runs.

Used by both ``panels/analysis.py`` (basic) and ``panels/batch_results.py`` (batch)
to replace the entire right-pane content while a run is in progress.

This gives exactly one Solara re-render when a run starts (spinner replaces content)
and one when it ends (results replace spinner).
"""

from __future__ import annotations

import solara


@solara.component
def RunSpinner(label: str = "Running\u2026") -> None:
    """Full-panel centered spinner — replaces entire results pane during a run."""
    with solara.Column(
        style=(
            "align-items: center; justify-content: center;"
            " min-height: 320px; gap: 16px;"
        )
    ):
        solara.v.ProgressCircular(indeterminate=True, color="primary", size=48, width=4)
        solara.Text(label, style="color: #888; font-style: italic;")
