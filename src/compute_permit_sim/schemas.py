"""Pydantic schemas for configuration and data validation."""

from pydantic import BaseModel, ConfigDict, Field


class AuditConfig(BaseModel):
    """Configuration for audit policies (The Governor)."""

    base_prob: float = Field(..., description="Base audit probability (pi_0)")
    high_prob: float = Field(..., description="High suspicion audit probability (pi_1)")
    signal_fpr: float = Field(..., description="False Positive Rate (alpha)")
    signal_tpr: float = Field(..., description="True Positive Rate (beta)")
    penalty_amount: float = Field(..., description="Effective penalty amount (P)")

    model_config = ConfigDict(frozen=True)


class MarketConfig(BaseModel):
    """Configuration for the Permit Market."""

    token_cap: float = Field(..., description="Total permits available (Q)")

    model_config = ConfigDict(frozen=True)


class LabConfig(BaseModel):
    """Configuration for Lab agents generation."""

    gross_value_min: float = 0.5
    gross_value_max: float = 1.5
    risk_profile_min: float = 0.8
    risk_profile_max: float = 1.2

    model_config = ConfigDict(frozen=True)


class ScenarioConfig(BaseModel):
    """Root configuration for a simulation scenario."""

    name: str = "Scenario"
    description: str = ""
    n_agents: int = Field(10, gt=0)
    steps: int = Field(10, gt=0)

    # Sub-configs
    audit: AuditConfig
    market: MarketConfig
    lab: LabConfig = Field(default_factory=LabConfig)

    seed: int | None = None
