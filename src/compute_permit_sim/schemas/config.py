"""Configuration schemas for the simulation."""

from pydantic import BaseModel, ConfigDict, Field

from compute_permit_sim.schemas.defaults import (
    DEFAULT_AUDIT_BACKCHECK_PROB,
    DEFAULT_AUDIT_BASE_PROB,
    DEFAULT_AUDIT_DECAY_RATE,
    DEFAULT_AUDIT_ESCALATION,
    DEFAULT_AUDIT_FALSE_NEG_RATE,
    DEFAULT_AUDIT_FALSE_POS_RATE,
    DEFAULT_AUDIT_MONITORING_PROB,
    DEFAULT_AUDIT_PENALTY_AMOUNT,
    DEFAULT_AUDIT_WHISTLEBLOWER_PROB,
    DEFAULT_CAPABILITY_SCALE,
    DEFAULT_COLLATERAL_AMOUNT,
    DEFAULT_FLOP_THRESHOLD,
    DEFAULT_FLOPS_PER_PERMIT,
    DEFAULT_LAB_AUDIT_COEFFICIENT,
    DEFAULT_LAB_CAPABILITY_VALUE,
    DEFAULT_LAB_COMPUTE_CAPACITY_MAX,
    DEFAULT_LAB_COMPUTE_CAPACITY_MIN,
    DEFAULT_LAB_ECON_VALUE_MAX,
    DEFAULT_LAB_ECON_VALUE_MIN,
    DEFAULT_LAB_RACING_FACTOR,
    DEFAULT_LAB_REPUTATION_SENSITIVITY,
    DEFAULT_LAB_RISK_PROFILE_MAX,
    DEFAULT_LAB_RISK_PROFILE_MIN,
    DEFAULT_MARKET_FIXED_PRICE,
    DEFAULT_MARKET_PERMIT_CAP,
    DEFAULT_RACING_GAP_SENSITIVITY,
    DEFAULT_REPUTATION_ESCALATION_FACTOR,
    DEFAULT_SCENARIO_N_AGENTS,
    DEFAULT_SCENARIO_STEPS,
    DEFAULT_SIGNAL_DEPENDENT,
    DEFAULT_SIGNAL_EXPONENT,
)

# ---------------------------------------------------------------------------
# UI metadata helpers — attached to each Field via json_schema_extra.
# Keys:
#   ui_group  – sidebar card / export section heading
#   ui_label  – human-readable control label
#   ui_format – rendering hint (percent | currency | scientific | int | float)
# ---------------------------------------------------------------------------


def _ui(
    group: str, label: str, fmt: str = "float", component: str | None = None
) -> dict:
    """Build json_schema_extra dict for a config field."""
    extra = {"ui_group": group, "ui_label": label, "ui_format": fmt}
    if component:
        extra["ui_component"] = component
    return extra


class AuditConfig(BaseModel):
    """Configuration for audit policies (The Auditor).

    Audit model has two stages:
    1. AUDIT OCCURRENCE: Whether an audit is initiated
       - base_prob (pi_0): baseline audit probability for all firms
       - signal_dependent: whether excess compute affects audit rate
       - When signal-dependent: p_audit = base_prob + signal × (1 - base_prob)
       - Signal strength scales with excess compute via signal_exponent

    2. AUDIT OUTCOME: Whether an audit catches a violator (if one exists)
       - false_positive_rate (alpha): P(false alarm | compliant firm audited)
       - false_negative_rate (beta): P(miss | non-compliant firm audited)
       - p_catch = (1 - beta) + beta × backcheck_prob
    """

    base_prob: float = Field(
        DEFAULT_AUDIT_BASE_PROB,
        ge=0,
        le=1,
        description="Base audit probability (pi_0)",
        json_schema_extra=_ui("Audit Policy", "Base π₀", "percent"),
    )
    signal_dependent: bool = Field(
        DEFAULT_SIGNAL_DEPENDENT,
        description="Enable signal-dependent auditing (excess compute affects audit rate)",
        json_schema_extra=_ui("Audit Policy", "Signal Dependent", "bool"),
    )
    signal_exponent: float = Field(
        DEFAULT_SIGNAL_EXPONENT,
        gt=0,
        description=(
            "Shape of excess→signal curve: "
            "1.0=linear, <1=concave (small excess detectable), "
            ">1=convex (only large excess visible)"
        ),
        json_schema_extra=_ui("Audit Policy", "Signal Exponent", "float"),
    )
    false_positive_rate: float = Field(
        DEFAULT_AUDIT_FALSE_POS_RATE,
        ge=0,
        le=1,
        description="P(false alarm | compliant firm audited) — alpha",
        json_schema_extra=_ui("Audit Policy", "Signal FPR", "percent"),
    )
    false_negative_rate: float = Field(
        DEFAULT_AUDIT_FALSE_NEG_RATE,
        ge=0,
        le=1,
        description="P(miss | non-compliant firm audited) — beta",
        json_schema_extra=_ui("Audit Policy", "Signal FNR (1-TPR)", "percent"),
    )
    penalty_amount: float = Field(
        DEFAULT_AUDIT_PENALTY_AMOUNT,
        ge=0,
        description="Amount applied as penalty if caught (M$)",
        json_schema_extra=_ui("Audit Policy", "Penalty (M$)", "currency"),
    )
    backcheck_prob: float = Field(
        DEFAULT_AUDIT_BACKCHECK_PROB,
        ge=0,
        le=1,
        description="Backcheck probability (p_b)",
        json_schema_extra=_ui("Audit Policy", "Backcheck Prob", "percent"),
    )
    whistleblower_prob: float = Field(
        DEFAULT_AUDIT_WHISTLEBLOWER_PROB,
        ge=0,
        le=1,
        description="Probability of detection by whistleblower (p_w)",
        json_schema_extra=_ui("Audit Policy", "Whistleblower Prob", "percent"),
    )
    monitoring_prob: float = Field(
        DEFAULT_AUDIT_MONITORING_PROB,
        ge=0,
        le=1,
        description="Global monitoring detection rate (p_m): hardware/electricity metering",
        json_schema_extra=_ui("Audit Policy", "Monitoring p_m", "percent"),
    )
    max_audits_per_step: int | None = Field(
        None,
        ge=0,
        description="Max number of audits allowed per step (budget constraint)",
        json_schema_extra=_ui("Audit Policy", "Max Audits/Step", "int"),
    )
    # Audit rate escalation (active when dynamic_factors=True)
    audit_escalation: float = Field(
        DEFAULT_AUDIT_ESCALATION,
        ge=0,
        description="Added to audit_coefficient on failed audit",
        json_schema_extra=_ui("Dynamic Factors", "Audit Escalation", "float"),
    )
    audit_decay_rate: float = Field(
        DEFAULT_AUDIT_DECAY_RATE,
        ge=0,
        le=1,
        description="Per-step decay factor for escalated audit coefficient",
        json_schema_extra=_ui("Dynamic Factors", "Audit Decay Rate", "percent"),
    )

    model_config = ConfigDict(frozen=True)


class MarketConfig(BaseModel):
    """Configuration for the Permit Market."""

    permit_cap: float = Field(
        DEFAULT_MARKET_PERMIT_CAP,
        gt=0,
        description="Total permits available (Q)",
        json_schema_extra=_ui("General", "Permit Cap (Q)", "float"),
    )
    fixed_price: float | None = Field(
        DEFAULT_MARKET_FIXED_PRICE,
        ge=0,
        description="Fixed price for unlimited permits (optional)",
        json_schema_extra=_ui("General", "Fixed Price (M$)", "currency"),
    )
    flops_per_permit: float | None = Field(
        DEFAULT_FLOPS_PER_PERMIT,
        gt=0,
        description="FLOPs covered by one permit. None = binary (0/1 per firm).",
        json_schema_extra=_ui("General", "FLOPs/Permit", "scientific"),
    )


class LabConfig(BaseModel):
    """Configuration for Lab agent generation.

    economic_value and risk_profile use min/max ranges because each agent is drawn
    from uniform(min, max) to create heterogeneous firms — this is the core
    source of agent diversity in the model.

    Other parameters are uniform across firms for MVP. Firm-specific heterogeneity
    for these can be added by converting to min/max ranges later.
    """

    economic_value_min: float = Field(
        DEFAULT_LAB_ECON_VALUE_MIN,
        json_schema_extra=_ui(
            "Lab Generation", "Econ Value Min (M$)", "currency", "range_min"
        ),
    )
    economic_value_max: float = Field(
        DEFAULT_LAB_ECON_VALUE_MAX,
        json_schema_extra=_ui(
            "Lab Generation", "Econ Value Max (M$)", "currency", "range_max"
        ),
    )
    risk_profile_min: float = Field(
        DEFAULT_LAB_RISK_PROFILE_MIN,
        json_schema_extra=_ui(
            "Lab Generation", "Risk Profile Min", "float", "range_min"
        ),
    )
    risk_profile_max: float = Field(
        DEFAULT_LAB_RISK_PROFILE_MAX,
        json_schema_extra=_ui(
            "Lab Generation", "Risk Profile Max", "float", "range_max"
        ),
    )
    capability_value: float = Field(
        DEFAULT_LAB_CAPABILITY_VALUE,
        ge=0,
        description="V_b: baseline value of model capabilities from training",
        json_schema_extra=_ui("Lab Generation", "Capability Vb (M$)", "currency"),
    )
    racing_factor: float = Field(
        DEFAULT_LAB_RACING_FACTOR,
        ge=0,
        description="c_r: urgency multiplier on capability value",
        json_schema_extra=_ui("Lab Generation", "Racing Factor cr", "float"),
    )
    reputation_sensitivity: float = Field(
        DEFAULT_LAB_REPUTATION_SENSITIVITY,
        ge=0,
        description="R: perceived reputation cost if caught",
        json_schema_extra=_ui("Lab Generation", "Reputation Sen. R (M$)", "currency"),
    )
    audit_coefficient: float = Field(
        DEFAULT_LAB_AUDIT_COEFFICIENT,
        ge=0,
        description="c(i): firm-specific audit rate scaling",
        json_schema_extra=_ui("Lab Generation", "Audit Coeff c(i)", "float"),
    )
    compute_capacity_min: float = Field(
        DEFAULT_LAB_COMPUTE_CAPACITY_MIN,
        ge=0,
        description="Min planned training run size (FLOP)",
        json_schema_extra=_ui(
            "Lab Generation", "Compute Cap Min", "scientific", "range_min"
        ),
    )
    compute_capacity_max: float = Field(
        DEFAULT_LAB_COMPUTE_CAPACITY_MAX,
        ge=0,
        description="Max planned training run size (FLOP)",
        json_schema_extra=_ui(
            "Lab Generation", "Compute Cap Max", "scientific", "range_max"
        ),
    )
    # Dynamic factor params (active when dynamic_factors=True on ScenarioConfig)
    reputation_escalation_factor: float = Field(
        DEFAULT_REPUTATION_ESCALATION_FACTOR,
        ge=0,
        description="Reputation increase per failed audit (0.5 = +50%)",
        json_schema_extra=_ui("Dynamic Factors", "Reputation Escalation", "float"),
    )
    racing_gap_sensitivity: float = Field(
        DEFAULT_RACING_GAP_SENSITIVITY,
        ge=0,
        description="How much capability gap affects racing factor",
        json_schema_extra=_ui("Dynamic Factors", "Racing Gap Sensitivity", "float"),
    )
    capability_scale: float = Field(
        DEFAULT_CAPABILITY_SCALE,
        gt=0,
        description="Normalization factor for capability gap",
        json_schema_extra=_ui("Dynamic Factors", "Capability Scale", "float"),
    )
    model_config = ConfigDict(frozen=True)


class ScenarioConfig(BaseModel):
    """Root configuration for a simulation scenario."""

    name: str = "Scenario"
    description: str = ""
    n_agents: int = Field(
        DEFAULT_SCENARIO_N_AGENTS,
        gt=0,
        json_schema_extra=_ui("General", "N Agents", "int"),
    )
    steps: int = Field(
        DEFAULT_SCENARIO_STEPS,
        gt=0,
        json_schema_extra=_ui("General", "Steps", "int"),
    )

    # Regulatory threshold: training runs require permits when
    # planned_training_flops > flop_threshold.
    # Signal strength for enforcement scales with excess above this value.
    flop_threshold: float = Field(
        DEFAULT_FLOP_THRESHOLD,
        ge=0,
        description="FLOP threshold for permit requirement (e.g. 1e25)",
        json_schema_extra=_ui("General", "FLOP Threshold", "scientific"),
    )

    # Collateral: refundable deposit posted before market participation.
    # Seized on verified violation; returned otherwise. 0 = no collateral.
    # Ref: Christoph (2026) §2.5 — collateral K relaxes limited liability.
    collateral_amount: float = Field(
        DEFAULT_COLLATERAL_AMOUNT,
        ge=0,
        description="Required collateral per lab (M$). 0 = disabled.",
        json_schema_extra=_ui("General", "Collateral (M$)", "currency"),
    )

    # Sub-configs
    audit: AuditConfig = Field(default_factory=AuditConfig)
    market: MarketConfig = Field(default_factory=MarketConfig)
    lab: LabConfig = Field(default_factory=LabConfig)

    seed: int | None = None
