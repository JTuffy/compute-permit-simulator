"""Visualization constants — colors, chart styling, CSS tokens."""

# Research Lab Theme
COLOR_LAB_PRIMARY = "#2196F3"
COLOR_LAB_SUCCESS = "#4CAF50"
COLOR_LAB_WARNING = "#FF9800"
COLOR_LAB_ERROR = "#F44336"
COLOR_LAB_INPUT_BG = "#F5F7FA"
COLOR_LAB_OUTPUT_BG = "#FFFFFF"
COLOR_LAB_METRIC_BG = "#E3F2FD"

# Chart Color Map
CHART_COLOR_MAP = {
    "green": COLOR_LAB_SUCCESS,
    "blue": COLOR_LAB_PRIMARY,
    "red": COLOR_LAB_ERROR,
    "orange": COLOR_LAB_WARNING,
}

# Outcome color tokens — used consistently across all charts
OUTCOME_COLORS: dict[str, str] = {
    "Compliant": COLOR_LAB_SUCCESS,  # green
    "Caught": "#212121",  # near-black
    "Uncaught": COLOR_LAB_ERROR,  # red
}
