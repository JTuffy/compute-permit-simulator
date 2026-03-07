"""Expandable chart wrapper — click button to open a correctly-sized dialog.

Layout-safe:
- No wrapper containers (Sheet, Card, etc.) around the inline chart
- Dialog sized to the Figure's pixel dimensions — no scrollbars
- solara.v.Dialog (Vuetify) — solara.lab.Dialog does not exist on this version

Comm safety:
- FigureMatplotlib creates a WebSocket comm channel per render.
  Rendering the same figure twice (inline + inside an always-present hidden
  Dialog) creates two comms — the hidden one goes stale and Solara drops both,
  causing the chart to disappear.
- Fix: the Dialog only renders FigureMatplotlib when it is actually open
  (expanded=True). When closed, the Dialog DOM node exists but is empty,
  so no stale comm is created.

PNG download:
- Pass ``download_filename`` to embed a download-PNG icon alongside the
  expand button.  All ``DownloadPNG`` wrappers in callers should be removed
  in favour of this parameter — the download lives with the chart, not the
  layout around it.
"""

from __future__ import annotations

import solara
from matplotlib.figure import Figure


@solara.component
def ExpandableChart(fig: Figure, download_filename: str | None = None) -> None:
    """Render a matplotlib figure with an expand button and optional PNG download.

    Drop-in replacement for ``solara.FigureMatplotlib``. The chart
    displays inline at its normal size. An expand icon below opens a
    dialog sized to fit the figure exactly — no scrollbars.

    Args:
        fig: The matplotlib figure to display.
        download_filename: If provided, a download-PNG icon is shown next to
            the expand button. The canonical filename (e.g. ``"mc_compliance.png"``)
            is used verbatim — callers should NOT also wrap the chart in
            ``DownloadPNG``; that would duplicate the button.
    """
    from compute_permit_sim.vis.components.results import DownloadPNG, fig_to_png

    expanded, set_expanded = solara.use_state(False)

    # Inline rendering — the only FigureMatplotlib render when dialog is closed.
    solara.FigureMatplotlib(fig)

    # Action row: optional PNG download + expand, right-aligned, low-opacity
    with solara.Row(style="justify-content: flex-end; gap: 2px; margin: -4px 0 4px;"):
        if download_filename is not None:
            DownloadPNG(
                "Download chart as PNG",
                lambda: fig_to_png(fig),
                download_filename,
            )
        solara.Button(
            label="",
            icon_name="mdi-arrow-expand-all",
            icon=True,
            small=True,
            on_click=lambda: set_expanded(True),
            style="opacity: 0.4;",
        )

    # Size dialog to the figure's pixel dimensions (+ a bit of padding)
    px_w = int(fig.get_figwidth() * fig.get_dpi()) + 32
    px_h = int(fig.get_figheight() * fig.get_dpi()) + 72  # room for close button

    with solara.v.Dialog(
        v_model=expanded,
        on_v_model=set_expanded,
        max_width=f"{px_w}px",
    ):
        # Only render FigureMatplotlib when the dialog is open.
        # This prevents a second (hidden) comm being created while the dialog
        # is closed — which caused the visible chart to go stale and disappear.
        if expanded:
            with solara.v.Card(
                style_=f"padding: 0; overflow: hidden; height: {px_h}px;"
            ):
                solara.FigureMatplotlib(fig)
                with solara.v.CardActions(style_="padding: 4px 8px;"):
                    solara.v.Spacer()
                    solara.Button(
                        "Close",
                        icon_name="mdi-close",
                        on_click=lambda: set_expanded(False),
                        small=True,
                        outlined=True,
                    )
