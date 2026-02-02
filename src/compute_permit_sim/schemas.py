"""Pydantic schemas for configuration and data validation."""

from pydantic import BaseModel, ConfigDict, Field


class AuditConfig(BaseModel):
    """Configuration for audit policies (The Auditor).

    Signal model: The auditor observes a noisy binary signal s_i for each firm.
        P(s=1 | compliant)     = false_positive_rate  (alpha)
        P(s=0 | non-compliant) = false_negative_rate  (1 - beta)

    Detection: p_eff = p_s + (1 - p_s) * backcheck_prob
        where p_s = (1 - false_negative_rate) * high_prob
                   + false_negative_rate * base_prob
    """

    base_prob: float = Field(
        ..., ge=0, le=1, description="Base audit probability (pi_0)"
    )
    high_prob: float = Field(
        ..., ge=0, le=1, description="High suspicion audit probability (pi_1)"
    )
    false_positive_rate: float = Field(
        ..., ge=0, le=1, description="P(signal=1 | compliant) — alpha"
    )
    false_negative_rate: float = Field(
        ..., ge=0, le=1, description="P(signal=0 | non-compliant) — 1 - beta"
    )
    penalty_amount: float = Field(
        ..., ge=0, description="Effective penalty amount (P = fine phi)"
    )
    backcheck_prob: float = Field(
        0.0, ge=0, le=1, description="Backcheck probability (p_b)"
    )
    whistleblower_prob: float = Field(
        0.0,
        ge=0,
        le=1,
        description="Probability of detection by whistleblower (p_w)",
    )
    max_audits_per_step: int | None = Field(
        None,
        ge=0,
        description="Max number of audits allowed per step (budget constraint)",
    )

    model_config = ConfigDict(frozen=True)


class MarketConfig(BaseModel):
    """Configuration for the Permit Market."""

    token_cap: float = Field(..., gt=0, description="Total permits available (Q)")
    fixed_price: float | None = Field(
        None, ge=0, description="Fixed price for unlimited permits (optional)"
    )

    def set_fixed_price(self, price: float) -> None:
        """Set a fixed price for the market (unlimited supply mode)."""
        object.__setattr__(self, "fixed_price", price)


class LabConfig(BaseModel):
    """Configuration for Lab agent generation.

    economic_value and risk_profile use min/max ranges because each agent is drawn
    from uniform(min, max) to create heterogeneous firms — this is the core
    source of agent diversity in the model.

    Other parameters are uniform across firms for MVP. Firm-specific heterogeneity
    for these can be added by converting to min/max ranges later.
    """

    economic_value_min: float = 0.5
    economic_value_max: float = 1.5
    risk_profile_min: float = 0.8
    risk_profile_max: float = 1.2
    capacity_min: float = Field(
        1.0, ge=0, description="Min compute capacity (q_max) for agent generation"
    )
    capacity_max: float = Field(
        2.0, ge=0, description="Max compute capacity (q_max) for agent generation"
    )
    capability_value: float = Field(
        0.0, ge=0, description="V_b: baseline value of model capabilities from training"
    )
    racing_factor: float = Field(
        1.0, ge=0, description="c_r: urgency multiplier on capability value"
    )
    reputation_sensitivity: float = Field(
        0.0, ge=0, description="R: perceived reputation cost if caught"
    )
    audit_coefficient: float = Field(
        1.0, ge=0, description="c(i): firm-specific audit rate scaling"
    )

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
