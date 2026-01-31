"""Pydantic schemas for configuration and data validation."""

from pydantic import BaseModel, ConfigDict, Field


class AuditConfig(BaseModel):
    """Configuration for audit policies (The Governor).

    Signal model: The governor observes a noisy binary signal s_i for each firm.
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

    model_config = ConfigDict(frozen=True)


class MarketConfig(BaseModel):
    """Configuration for the Permit Market."""

    token_cap: float = Field(..., gt=0, description="Total permits available (Q)")
    fixed_price: float | None = Field(
        None, ge=0, description="Fixed price for unlimited permits (optional)"
    )

    model_config = ConfigDict(frozen=True)


class LabConfig(BaseModel):
    """Configuration for Lab agent generation.

    gross_value and risk_profile use min/max ranges because each agent is drawn
    from uniform(min, max) to create heterogeneous firms — this is the core
    source of agent diversity in the model.

    Other parameters are uniform across firms for MVP. Firm-specific heterogeneity
    for these can be added by converting to min/max ranges later.
    """

    gross_value_min: float = 0.5
    gross_value_max: float = 1.5
    risk_profile_min: float = 0.8
    risk_profile_max: float = 1.2
    capability_value: float = Field(
        0.0, ge=0, description="V_b: baseline value of model capabilities"
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
    n_agents: int = Field(10, gt=0)
    steps: int = Field(10, gt=0)

    # Sub-configs
    audit: AuditConfig
    market: MarketConfig
    lab: LabConfig = Field(default_factory=LabConfig)

    seed: int | None = None
