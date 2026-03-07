"""Shared enumerations for the simulation data model."""

from enum import Enum


class AuditSource(str, Enum):
    """The specific detection channel that caught a violation."""

    DIRECT = "direct"
    BACKCHECK = "backcheck"
    WHISTLEBLOWER = "whistleblower"
    MONITORING = "monitoring"
