"""Control components for simulation UI."""

import solara


@solara.component
def RangeView(label: str, min_val: float, max_val: float):
    """Read-only display of a min-max range."""
    solara.Markdown(f"*{label}*")
    solara.InputFloat(label="Min", value=min_val, disabled=True)
    solara.InputFloat(label="Max", value=max_val, disabled=True)


@solara.component
def RangeController(label: str, min_reactive, max_reactive):
    """Compact interactive control for a min-max range."""
    with solara.Column(style="margin-bottom: 8px;"):
        solara.Text(label, style="font-size: 0.85rem; font-weight: 500; color: #666;")
        with solara.Row(style="align-items: center; margin-top: -4px;"):
            solara.InputFloat(
                label="Min", value=min_reactive, continuous_update=True, dense=True
            )
            solara.Text("-", style="margin: 0 4px;")
            solara.InputFloat(
                label="Max", value=max_reactive, continuous_update=True, dense=True
            )
