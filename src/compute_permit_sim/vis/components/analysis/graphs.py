import pandas as pd
import solara

from compute_permit_sim.vis.plotting import plot_time_series


@solara.component
def RunGraphs(compliance_series: pd.Series, price_series: pd.Series):
    """Reusable component for displaying run metrics graphs."""
    with solara.Card("Time Series Analysis"):
        with solara.Columns([1, 1]):
            with solara.Column():
                if compliance_series:
                    fig = plot_time_series(
                        compliance_series, "Compliance", "green", ylim=(-0.05, 1.05)
                    )
                    solara.FigureMatplotlib(fig)
                else:
                    solara.Markdown("No Data")

            with solara.Column():
                if price_series:
                    fig = plot_time_series(price_series, "Price", "blue")
                    solara.FigureMatplotlib(fig)
                else:
                    solara.Markdown("No Data")
