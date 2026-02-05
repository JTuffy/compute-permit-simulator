"""Pydantic schemas for configuration and data validation."""

from pydantic import BaseModel, ConfigDict, Field


from compute_permit_sim.core.constants import (
    DEFAULT_AUDIT_BACKCHECK_PROB,
    DEFAULT_AUDIT_BASE_PROB,
    DEFAULT_AUDIT_FALSE_NEG_RATE,
    DEFAULT_AUDIT_FALSE_POS_RATE,
    DEFAULT_AUDIT_HIGH_PROB,
    DEFAULT_AUDIT_PENALTY_AMOUNT,
    DEFAULT_AUDIT_WHISTLEBLOWER_PROB,
    DEFAULT_LAB_AUDIT_COEFFICIENT,
    DEFAULT_LAB_CAPABILITY_VALUE,
    DEFAULT_LAB_CAPACITY_MAX,
    DEFAULT_LAB_CAPACITY_MIN,
    DEFAULT_LAB_ECON_VALUE_MAX,
    DEFAULT_LAB_ECON_VALUE_MIN,
    DEFAULT_LAB_RACING_FACTOR,
    DEFAULT_LAB_REPUTATION_SENSITIVITY,
    DEFAULT_LAB_RISK_PROFILE_MAX,
    DEFAULT_LAB_RISK_PROFILE_MIN,
    DEFAULT_SCENARIO_N_AGENTS,
    DEFAULT_SCENARIO_STEPS,
)


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
        DEFAULT_AUDIT_BASE_PROB, ge=0, le=1, description="Base audit probability (pi_0)"
    )
    high_prob: float = Field(
        DEFAULT_AUDIT_HIGH_PROB,
        ge=0,
        le=1,
        description="High suspicion audit probability (pi_1)",
    )
    false_positive_rate: float = Field(
        DEFAULT_AUDIT_FALSE_POS_RATE,
        ge=0,
        le=1,
        description="P(signal=1 | compliant) — alpha",
    )
    false_negative_rate: float = Field(
        DEFAULT_AUDIT_FALSE_NEG_RATE,
        ge=0,
        le=1,
        description="P(signal=0 | non-compliant) — 1 - beta",
    )
    penalty_amount: float = Field(
        DEFAULT_AUDIT_PENALTY_AMOUNT,
        ge=0,
        description="Effective penalty amount (P = fine phi)",
    )
    backcheck_prob: float = Field(
        DEFAULT_AUDIT_BACKCHECK_PROB,
        ge=0,
        le=1,
        description="Backcheck probability (p_b)",
    )
    whistleblower_prob: float = Field(
        DEFAULT_AUDIT_WHISTLEBLOWER_PROB,
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

    economic_value_min: float = DEFAULT_LAB_ECON_VALUE_MIN
    economic_value_max: float = DEFAULT_LAB_ECON_VALUE_MAX
    risk_profile_min: float = DEFAULT_LAB_RISK_PROFILE_MIN
    risk_profile_max: float = DEFAULT_LAB_RISK_PROFILE_MAX
    capacity_min: float = Field(
        DEFAULT_LAB_CAPACITY_MIN,
        ge=0,
        description="Min compute capacity (q_max) for agent generation",
    )
    capacity_max: float = Field(
        DEFAULT_LAB_CAPACITY_MAX,
        ge=0,
        description="Max compute capacity (q_max) for agent generation",
    )
    capability_value: float = Field(
        DEFAULT_LAB_CAPABILITY_VALUE,
        ge=0,
        description="V_b: baseline value of model capabilities from training",
    )
    racing_factor: float = Field(
        DEFAULT_LAB_RACING_FACTOR,
        ge=0,
        description="c_r: urgency multiplier on capability value",
    )
    reputation_sensitivity: float = Field(
        DEFAULT_LAB_REPUTATION_SENSITIVITY,
        ge=0,
        description="R: perceived reputation cost if caught",
    )
    audit_coefficient: float = Field(
        DEFAULT_LAB_AUDIT_COEFFICIENT,
        ge=0,
        description="c(i): firm-specific audit rate scaling",
    )

    model_config = ConfigDict(frozen=True)


class ScenarioConfig(BaseModel):
    """Root configuration for a simulation scenario."""

    name: str = "Scenario"
    description: str = ""
    n_agents: int = Field(DEFAULT_SCENARIO_N_AGENTS, gt=0)
    steps: int = Field(DEFAULT_SCENARIO_STEPS, gt=0)

    # Sub-configs
    audit: AuditConfig
    market: MarketConfig
    lab: LabConfig = Field(default_factory=LabConfig)

    seed: int | None = None


class AgentSnapshot(BaseModel):
    """Standardized snapshot of a single agent's state at one step."""

    id: int = Field(..., description="Unique agent identifier")
    capacity: float = Field(..., description="Max compute capacity")
    has_permit: bool = Field(..., description="Whether the agent holds a permit")
    used_compute: float = Field(..., description="Actual compute units consumed")
    reported_compute: float = Field(
        ..., description="Compute usage reported to regulator"
    )
    is_compliant: bool = Field(..., description="Compliance status")
    was_audited: bool = Field(..., description="Audit status this step")
    was_caught: bool = Field(..., description="Caught cheating this step")
    penalty_amount: float = Field(..., description="Penalty applied this step")
    revenue: float = Field(..., description="Gross economic value generated")
    economic_value: float = Field(..., description="Agent's base economic value (v_i)")
    risk_profile: float = Field(..., description="Agent's risk profile")
    step_profit: float = Field(..., description="Net profit/loss this step")
    wealth: float = Field(..., description="Cumulative wealth")

    model_config = ConfigDict(frozen=True)


class StepResult(BaseModel):
    """Snapshot of a single simulation step."""

    step: int
    market: dict = Field(..., description="Market state (price, volume, supply)")
    agents: list[AgentSnapshot] = Field(..., description="List of all agent states")
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
