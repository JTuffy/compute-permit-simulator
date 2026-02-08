"""Centralized constants for the Compute Permit Simulator.

This file contains default values for:
- Audit parameters
- Market configurations
- Lab agent generation
- CSS Colors and Styling defaults
"""

# --- Audit Policy Defaults ---
DEFAULT_AUDIT_BASE_PROB = 0.1  # pi_0
DEFAULT_AUDIT_HIGH_PROB = 0.1  # pi_1
DEFAULT_AUDIT_FALSE_POS_RATE = 0.0  # alpha
DEFAULT_AUDIT_FALSE_NEG_RATE = 0.0  # 1 - beta
DEFAULT_AUDIT_PENALTY_AMOUNT = 1.0  # phi (fixed amount for MVP)
DEFAULT_AUDIT_BACKCHECK_PROB = 0.0  # p_b
DEFAULT_AUDIT_WHISTLEBLOWER_PROB = 0.0  # p_w
DEFAULT_AUDIT_COST = 1.0  # Cost per audit for regulator

# --- Market Defaults ---
DEFAULT_MARKET_TOKEN_CAP = 20.0
DEFAULT_MARKET_FIXED_PRICE = None

# --- Lab Agent Defaults ---
DEFAULT_LAB_ECON_VALUE_MIN = 0.5
DEFAULT_LAB_ECON_VALUE_MAX = 1.5
DEFAULT_LAB_RISK_PROFILE_MIN = 0.8
DEFAULT_LAB_RISK_PROFILE_MAX = 1.2
DEFAULT_LAB_CAPACITY_MIN = 1.0
DEFAULT_LAB_CAPACITY_MAX = 2.0
DEFAULT_LAB_CAPABILITY_VALUE = 0.0  # V_b
DEFAULT_LAB_RACING_FACTOR = 1.0  # c_r
DEFAULT_LAB_REPUTATION_SENSITIVITY = 0.0  # R
DEFAULT_LAB_AUDIT_COEFFICIENT = 1.0  # c(i)

# --- Scenario Defaults ---
DEFAULT_SCENARIO_N_AGENTS = 50
DEFAULT_SCENARIO_STEPS = 10


# --- Dataframe Column Names (Strong Typing) ---
class ColumnNames:
    """Strongly typed column names for AgentSnapshot DataFrames."""

    ID = "id"
    CAPACITY = "capacity"
    HAS_PERMIT = "has_permit"
    USED_COMPUTE = "used_compute"
    REPORTED_COMPUTE = "reported_compute"
    IS_COMPLIANT = "is_compliant"
    WAS_AUDITED = "was_audited"
    WAS_CAUGHT = "was_caught"
    PENALTY_AMOUNT = "penalty_amount"
    REVENUE = "revenue"
    ECONOMIC_VALUE = "economic_value"
    RISK_PROFILE = "risk_profile"
    STEP_PROFIT = "step_profit"
    WEALTH = "wealth"


# --- UI / Visualization / CSS Colors ---
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
