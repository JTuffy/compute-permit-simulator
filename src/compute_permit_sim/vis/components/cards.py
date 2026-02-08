import solara


@solara.component
def MetricCard(
    label: str, value: str, color_variant: str = "primary"
) -> solara.Element:
    """Display a primary metric with visual hierarchy."""
    # Custom compact styling via CSS classes or inline style
    style = "padding: 12px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); background-color: white;"
    border = (
        "4px solid #1976D2"
        if color_variant == "primary"
        else "4px solid #4CAF50"
        if color_variant == "success"
        else "4px solid #FF9800"
    )

    with solara.Column(style=f"{style} border-left: {border}; margin: 4px;"):
        solara.HTML(
            tag="div",
            style="font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px;",
            unsafe_innerHTML=label,
        )
        solara.HTML(
            tag="div",
            style="font-size: 1.8rem; font-weight: 500;",
            unsafe_innerHTML=value,
        )


@solara.component
def ScenarioCard(title: str, children: list[solara.Element] = []) -> solara.Element:
    """Compact card for scenario configuration sections.

    Args:
        title: Section title (e.g., "General", "Audit Policy")
        children: Child elements (sliders, inputs)
    """
    with solara.Card(title=None, margin=2, style="min-width: 250px; flex: 1;"):
        solara.HTML(
            tag="h4",
            style="margin-top: 0; margin-bottom: 12px; border-bottom: 2px solid #f0f0f0; padding-bottom: 8px;",
            unsafe_innerHTML=title,
        )
        solara.Column(children=children)
