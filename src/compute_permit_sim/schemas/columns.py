"""Strongly typed column names for AgentSnapshot DataFrames.

Defines the data contract between schemas and consumers (vis, export).
"""


class ColumnNames:
    """Column name constants matching AgentSnapshot field names."""

    ID = "id"
    COMPUTE_CAPACITY = "compute_capacity"
    PLANNED_TRAINING_FLOPS = "planned_training_flops"
    USED_TRAINING_FLOPS = "used_training_flops"
    REPORTED_TRAINING_FLOPS = "reported_training_flops"
    HAS_PERMIT = "has_permit"
    IS_COMPLIANT = "is_compliant"
    WAS_AUDITED = "was_audited"
    WAS_CAUGHT = "was_caught"
    PENALTY_AMOUNT = "penalty_amount"
    ECONOMIC_VALUE = "economic_value"
    RISK_PROFILE = "risk_profile"
