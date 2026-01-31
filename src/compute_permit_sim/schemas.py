"""Pydantic schemas for configuration and data validation."""

from pydantic import BaseModel, ConfigDict, Field


class AuditConfig(BaseModel):
    """Configuration for audit policies (The Governor)."""

    base_prob: float = Field(..., description="Base audit probability (pi_0)")
    high_prob: float = Field(..., description="High suspicion audit probability (pi_1)")
    signal_fpr: float = Field(..., description="False Positive Rate (alpha)")
    signal_tpr: float = Field(..., description="True Positive Rate (beta)")
    penalty_amount: float = Field(..., description="Effective penalty amount (P)")
    audit_budget: int = Field(5, description="Max audits per step (Budget)")

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
    # Capability: Max compute a lab can run (defines their 'scale')
    capability_min: float = 1.0
    capability_max: float = 10.0
    # Allowance: Initial permits allocated (Grandfathering)
    allowance_min: float = 0.0
    allowance_max: float = 5.0
    # Collateral: Amount posted by lab (seized on fraud)
    collateral_min: float = 0.5
    collateral_max: float = 2.0

    model_config = ConfigDict(frozen=True)


class ScenarioConfig(BaseModel):
    """Root configuration for a simulation scenario."""

    name: str = "Scenario"
    description: str = ""
    n_agents: int = Field(5, gt=0)
    steps: int = Field(10, gt=0)

    # Sub-configs
    audit: AuditConfig
    market: MarketConfig
    lab: LabConfig = Field(default_factory=LabConfig)

    seed: int | None = None


class StepResult(BaseModel):
    """Snapshot of a single simulation step."""

    step_id: int
    market: dict = Field(..., description="Market state (price, volume, supply)")
    agents: list[dict] = Field(..., description="List of all agent states")
    audit: list[dict] = Field(
        default_factory=list, description="Audit events this step"
    )

    model_config = ConfigDict(frozen=True)


class SimulationRun(BaseModel):
    """Encapsulation of a full simulation run."""

    id: str = Field(..., description="Unique run identifier (timestamp/uuid)")
    config: ScenarioConfig
    steps: list[StepResult] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict, description="Aggregate metrics")

    model_config = ConfigDict(frozen=True)
