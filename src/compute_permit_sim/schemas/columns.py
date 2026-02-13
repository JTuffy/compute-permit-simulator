"""Strongly typed column names for AgentSnapshot DataFrames.

Defines the data contract between schemas and consumers (vis, export).
"""


class ColumnNames:
    """Column name constants matching AgentSnapshot field names."""

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
