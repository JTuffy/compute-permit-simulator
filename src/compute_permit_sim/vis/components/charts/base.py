"""Base utilities and types for chart components."""

from dataclasses import dataclass

import pandas as pd


@dataclass
class PlotConfig:
    """Configuration for standard plot styling."""

    figsize: tuple[int, int] = (6, 4)
    dpi: int = 100
    title: str | None = None
    xlabel: str | None = None
    ylabel: str | None = None
    grid: bool = True
    grid_alpha: float = 0.25


def validate_dataframe(
    df: pd.DataFrame | None,
    required_cols: list[str],
    error_msg: str = "Missing required columns for plot.",
) -> bool:
    """Validate that a DataFrame exists and has all required columns.

    Returns:
        True if valid, False otherwise. Caller is responsible for error handling.
    """
    if df is None or df.empty:
        return False
    return all(col in df.columns for col in required_cols)


def apply_standard_styling(ax, config: PlotConfig) -> None:
    """Apply standard styling to a matplotlib axis."""
    if config.grid:
        ax.grid(True, alpha=config.grid_alpha, linestyle="--", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.2)
    ax.spines["bottom"].set_linewidth(1.2)

    if config.title:
        ax.set_title(config.title, fontsize=12, fontweight="600")
    if config.xlabel:
        ax.set_xlabel(config.xlabel, fontsize=11, fontweight="500")
    if config.ylabel:
        ax.set_ylabel(config.ylabel, fontsize=11, fontweight="500")
