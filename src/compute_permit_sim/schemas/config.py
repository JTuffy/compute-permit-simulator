"""Configuration schemas for the simulation."""

from pydantic import BaseModel, ConfigDict, Field

from compute_permit_sim.core.constants import (
    DEFAULT_AUDIT_BACKCHECK_PROB,
    DEFAULT_AUDIT_BASE_PROB,
    DEFAULT_AUDIT_COST,
    DEFAULT_AUDIT_DECAY_RATE,
    DEFAULT_AUDIT_ESCALATION,
    DEFAULT_AUDIT_FALSE_NEG_RATE,
    DEFAULT_AUDIT_FALSE_POS_RATE,
    DEFAULT_AUDIT_HIGH_PROB,
    DEFAULT_AUDIT_PENALTY_AMOUNT,
    DEFAULT_AUDIT_PENALTY_CEILING,
    DEFAULT_AUDIT_PENALTY_FIXED,
    DEFAULT_AUDIT_PENALTY_PERCENTAGE,
    DEFAULT_AUDIT_WHISTLEBLOWER_PROB,
    DEFAULT_CAPABILITY_SCALE,
    DEFAULT_COLLATERAL_AMOUNT,
    DEFAULT_FLOP_THRESHOLD,
    DEFAULT_LAB_AUDIT_COEFFICIENT,
    DEFAULT_LAB_CAPABILITY_VALUE,
    DEFAULT_LAB_CAPACITY_MAX,
    DEFAULT_LAB_CAPACITY_MIN,
    DEFAULT_LAB_ECON_VALUE_MAX,
    DEFAULT_LAB_ECON_VALUE_MIN,
    DEFAULT_LAB_FIRM_REVENUE_MAX,
    DEFAULT_LAB_FIRM_REVENUE_MIN,
    DEFAULT_LAB_RACING_FACTOR,
    DEFAULT_LAB_REPUTATION_SENSITIVITY,
    DEFAULT_LAB_RISK_PROFILE_MAX,
    DEFAULT_LAB_RISK_PROFILE_MIN,
    DEFAULT_LAB_TRAINING_FLOPS_MAX,
    DEFAULT_LAB_TRAINING_FLOPS_MIN,
    DEFAULT_RACING_GAP_SENSITIVITY,
    DEFAULT_REPUTATION_ESCALATION_FACTOR,
    DEFAULT_SCENARIO_N_AGENTS,
    DEFAULT_SCENARIO_STEPS,
)


class UrlConfig(BaseModel):
    """Schema for URL state synchronization (abbreviated keys)."""

    n_agents: int | None = None
    steps: int | None = None
    token_cap: float | None = None
    seed: int | None = None
    penalty: float | None = None
    base_prob: float | None = None
    high_prob: float | None = None
    signal_fpr: float | None = None
    signal_tpr: float | None = None
    backcheck_prob: float | None = None
    ev_min: float | None = None
    ev_max: float | None = None
    risk_min: float | None = None
    risk_max: float | None = None
    cap_min: float | None = None
    cap_max: float | None = None
    vb: float | None = None
    cr: float | None = None
    rep: float | None = None
    audit_coeff: float | None = None

    model_config = ConfigDict(frozen=True)


class AuditConfig(BaseModel):
    """Configuration for audit policies (The Auditor).

    Audit model has two stages:
    1. AUDIT OCCURRENCE: Whether an audit is initiated
       - base_prob (pi_0): baseline audit probability for all firms
       - high_prob (pi_1): elevated audit probability given suspicious signal
       - Signal strength for non-compliant firms scales with compute excess

    2. AUDIT OUTCOME: Whether an audit catches a violator (if one exists)
       - false_positive_rate (alpha): P(false alarm | compliant firm audited)
       - false_negative_rate (beta): P(miss | non-compliant firm audited)

    Detection: p_eff = p_s + (1 - p_s) * backcheck_prob
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
        description="P(false alarm | compliant firm audited) — alpha",
    )
    false_negative_rate: float = Field(
        DEFAULT_AUDIT_FALSE_NEG_RATE,
        ge=0,
        le=1,
        description="P(miss | non-compliant firm audited) — beta",
    )
    penalty_amount: float = Field(
        DEFAULT_AUDIT_PENALTY_AMOUNT,
        ge=0,
        description="Legacy flat penalty amount (used when penalty_fixed is not set)",
    )
    penalty_fixed: float = Field(
        DEFAULT_AUDIT_PENALTY_FIXED,
        ge=0,
        description="Fixed penalty floor (M$) — like EU AI Act €35M",
    )
    penalty_percentage: float = Field(
        DEFAULT_AUDIT_PENALTY_PERCENTAGE,
        ge=0,
        le=1.0,
        description="Percentage of firm value — like EU AI Act 7% turnover",
    )
    penalty_ceiling: float | None = Field(
        DEFAULT_AUDIT_PENALTY_CEILING,
        ge=0,
        description="Optional cap on total penalty (M$) — None means no cap",
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
    cost: float = Field(
        DEFAULT_AUDIT_COST,
        ge=0,
        description="Cost per audit for the regulator",
    )
    max_audits_per_step: int | None = Field(
        None,
        ge=0,
        description="Max number of audits allowed per step (budget constraint)",
    )
    # Audit rate escalation (active when dynamic_factors=True)
    audit_escalation: float = Field(
        DEFAULT_AUDIT_ESCALATION,
        ge=0,
        description="Added to audit_coefficient on failed audit",
    )
    audit_decay_rate: float = Field(
        DEFAULT_AUDIT_DECAY_RATE,
        ge=0,
        le=1,
        description="Per-step decay factor for escalated audit coefficient",
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
    firm_revenue_min: float = Field(
        DEFAULT_LAB_FIRM_REVENUE_MIN,
        ge=0,
        description="Min annual revenue/turnover (M$) for penalty calculation",
    )
    firm_revenue_max: float = Field(
        DEFAULT_LAB_FIRM_REVENUE_MAX,
        ge=0,
        description="Max annual revenue/turnover (M$) for penalty calculation",
    )
    training_flops_min: float = Field(
        DEFAULT_LAB_TRAINING_FLOPS_MIN,
        ge=0,
        description="Min planned training run size (FLOP)",
    )
    training_flops_max: float = Field(
        DEFAULT_LAB_TRAINING_FLOPS_MAX,
        ge=0,
        description="Max planned training run size (FLOP)",
    )
    # Dynamic factor params (active when dynamic_factors=True on ScenarioConfig)
    reputation_escalation_factor: float = Field(
        DEFAULT_REPUTATION_ESCALATION_FACTOR,
        ge=0,
        description="Reputation increase per failed audit (0.5 = +50%)",
    )
    racing_gap_sensitivity: float = Field(
        DEFAULT_RACING_GAP_SENSITIVITY,
        ge=0,
        description="How much capability gap affects racing factor",
    )
    capability_scale: float = Field(
        DEFAULT_CAPABILITY_SCALE,
        gt=0,
        description="Normalization factor for capability gap",
    )

    model_config = ConfigDict(frozen=True)


class ScenarioConfig(BaseModel):
    """Root configuration for a simulation scenario."""

    name: str = "Scenario"
    description: str = ""
    n_agents: int = Field(DEFAULT_SCENARIO_N_AGENTS, gt=0)
    steps: int = Field(DEFAULT_SCENARIO_STEPS, gt=0)

    # Regulatory threshold: training runs require permits when
    # planned_training_flops > flop_threshold.
    # Signal strength for enforcement scales with excess above this value.
    flop_threshold: float = Field(
        DEFAULT_FLOP_THRESHOLD,
        ge=0,
        description="FLOP threshold for permit requirement (e.g. 1e25)",
    )

    # Collateral: refundable deposit posted before market participation.
    # Seized on verified violation; returned otherwise. 0 = no collateral.
    # Ref: Christoph (2026) §2.5 — collateral K relaxes limited liability.
    collateral_amount: float = Field(
        DEFAULT_COLLATERAL_AMOUNT,
        ge=0,
        description="Required collateral per lab (M$). 0 = disabled.",
    )

    # Sub-configs
    audit: AuditConfig
    market: MarketConfig
    lab: LabConfig = Field(default_factory=LabConfig)

    seed: int | None = None
