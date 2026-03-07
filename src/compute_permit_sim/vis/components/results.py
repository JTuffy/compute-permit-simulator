"""Shared result-display primitives for all results panels.

Used by ``vis/components/analysis/summary.py`` and ``vis/panels/batch_results.py``
to ensure consistent chip style, icon download buttons, and figure rendering
across basic, Monte Carlo, and sweep result views.

Any new result panel should import from here rather than re-implementing
these patterns inline.
"""

from __future__ import annotations

import io
from typing import Callable

import solara
from matplotlib.figure import Figure

# ---------------------------------------------------------------------------
# Metric chip
# ---------------------------------------------------------------------------


@solara.component
def MetricChip(label: str, value: str) -> None:
    """Small ``label: value`` display — used in every Summary card header row."""
    solara.Markdown(f"**{label}:** {value}", style="white-space: nowrap;")


@solara.component
def SidebarLabel(text: str) -> None:
    """Section heading label for sidebar panels (SCENARIO, RUN HISTORY, etc.).

    ``solara.Markdown`` does not support ``classes=`` — this wraps the Markdown
    in a container with the CSS class so the stylesheet selector
    ``.sidebar-section-label .solara-markdown p`` applies correctly.
    """
    with solara.Column(classes=["sidebar-section-label"], style="margin: 0; gap: 0;"):
        solara.Markdown(text)


@solara.component
def SidebarHint(text: str) -> None:
    """Small muted hint/descriptor text below inputs or history items.

    ``solara.Markdown`` does not support ``classes=`` — wraps in a container
    so ``.sidebar-hint-text .solara-markdown p`` applies.
    """
    with solara.Column(classes=["sidebar-hint-text"], style="margin: 0; gap: 0;"):
        solara.Markdown(text)


@solara.component
def ResultsActions(children: list[solara.Element] = []) -> None:  # noqa: B006 — Solara expects list default
    """Bordered right-side icon cluster — identical across all results Summary cards.

    Usage::

        with ResultsActions():
            DownloadCSV(...)
            DownloadJSON(...)

    A light vertical separator visually groups action buttons away from the
    metric chips, making the actions feel like a distinct subsection.
    The `children` default must be ``[]``, not ``None``— Solara inspects
    component signatures at the framework level and requires a list default
    to inject child elements created inside the ``with`` context manager.
    """
    # flex-shrink/align-items/justify-content/gap are structural — allowed inline
    with solara.Column(
        style=(
            "border-left: 1px solid rgba(128,128,128,0.2);"
            " padding-left: 10px; flex-shrink: 0;"
            " align-items: center; justify-content: center; gap: 2px;"
        )
    ):
        for child in children:
            solara.display(child)


# ---------------------------------------------------------------------------
# Figure helper
# ---------------------------------------------------------------------------


def fig_to_png(fig: Figure, dpi: int = 130) -> bytes:
    """Render a Matplotlib figure to PNG bytes (for download buttons).

    Keeps dpi consistent across all export paths.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Download action buttons — icon-only, tooltip-labelled
# ---------------------------------------------------------------------------


def DownloadCSV(
    tooltip: str, data_fn: Callable[[], bytes | str], filename: str
) -> None:
    """Icon-only CSV download button with tooltip."""
    with solara.Tooltip(tooltip):
        with solara.FileDownload(data=data_fn, filename=filename, mime_type="text/csv"):
            solara.Button(icon_name="mdi-file-delimited-outline", icon=True, small=True)


def DownloadExcel(
    tooltip: str, data_fn: Callable[[], bytes | str], filename: str
) -> None:
    """Icon-only Excel download button with tooltip."""
    with solara.Tooltip(tooltip):
        with solara.FileDownload(
            data=data_fn,
            filename=filename,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ):
            solara.Button(icon_name="mdi-file-excel-outline", icon=True, small=True)


def DownloadPNG(tooltip: str, data_fn: Callable[[], bytes], filename: str) -> None:
    """Icon-only PNG download button with tooltip."""
    with solara.Tooltip(tooltip):
        with solara.FileDownload(
            data=data_fn, filename=filename, mime_type="image/png"
        ):
            solara.Button(icon_name="mdi-file-image-outline", icon=True, small=True)


def DownloadTeX(
    tooltip: str, data_fn: Callable[[], bytes | str], filename: str
) -> None:
    """Icon-only LaTeX download button with tooltip."""
    with solara.Tooltip(tooltip):
        with solara.FileDownload(
            data=data_fn, filename=filename, mime_type="text/plain"
        ):
            solara.Button(icon_name="mdi-code-braces", icon=True, small=True)


def DownloadJSON(
    tooltip: str, data_fn: Callable[[], bytes | str], filename: str
) -> None:
    """Icon-only JSON download button with tooltip.

    Use for full run export / reproducibility (``SimulationRun.model_dump_json``).
    """
    with solara.Tooltip(tooltip):
        with solara.FileDownload(
            data=data_fn, filename=filename, mime_type="application/json"
        ):
            solara.Button(icon_name="mdi-code-json", icon=True, small=True)
