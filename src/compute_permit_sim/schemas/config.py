"""Configuration schemas for the simulation."""

from pydantic import BaseModel, ConfigDict, Field

from compute_permit_sim.core.constants import (
    DEFAULT_AUDIT_BACKCHECK_PROB,
    DEFAULT_AUDIT_BASE_PROB,
    DEFAULT_AUDIT_COST,
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


# --- UI Configuration Models (for vis/state) ---
class UIAuditState(BaseModel):
    """Typed model for audit-related UI state."""

    base_prob: float = Field(
        DEFAULT_AUDIT_BASE_PROB, ge=0, le=1, description="Base audit probability"
    )
    high_prob: float = Field(
        DEFAULT_AUDIT_HIGH_PROB, ge=0, le=1, description="High suspicion probability"
    )
    false_positive_rate: float = Field(
        DEFAULT_AUDIT_FALSE_POS_RATE, ge=0, le=1, description="Signal FPR (alpha)"
    )
    false_negative_rate: float = Field(
        DEFAULT_AUDIT_FALSE_NEG_RATE, ge=0, le=1, description="1 - Signal TPR (1-beta)"
    )
    penalty: float = Field(
        DEFAULT_AUDIT_PENALTY_AMOUNT, ge=0, description="Penalty amount"
    )
    backcheck_prob: float = Field(
        DEFAULT_AUDIT_BACKCHECK_PROB, ge=0, le=1, description="Backcheck probability"
    )
    cost: float = Field(DEFAULT_AUDIT_COST, ge=0, description="Cost per audit")

    model_config = ConfigDict(frozen=False)


class UILabState(BaseModel):
    """Typed model for lab/firm-related UI state."""

    economic_value_min: float = DEFAULT_LAB_ECON_VALUE_MIN
    economic_value_max: float = DEFAULT_LAB_ECON_VALUE_MAX
    risk_profile_min: float = DEFAULT_LAB_RISK_PROFILE_MIN
    risk_profile_max: float = DEFAULT_LAB_RISK_PROFILE_MAX
    capacity_min: float = Field(
        DEFAULT_LAB_CAPACITY_MIN, ge=0, description="Min capacity"
    )
    capacity_max: float = Field(
        DEFAULT_LAB_CAPACITY_MAX, ge=0, description="Max capacity"
    )
    capability_value: float = Field(
        DEFAULT_LAB_CAPABILITY_VALUE, ge=0, description="V_b: capability value"
    )
    racing_factor: float = Field(
        DEFAULT_LAB_RACING_FACTOR, ge=0, description="c_r: racing urgency"
    )
    reputation_sensitivity: float = Field(
        DEFAULT_LAB_REPUTATION_SENSITIVITY, ge=0, description="R: reputation cost"
    )
    audit_coefficient: float = Field(
        DEFAULT_LAB_AUDIT_COEFFICIENT, ge=0, description="Audit rate scaling"
    )

    model_config = ConfigDict(frozen=False)


class UIMarketState(BaseModel):
    """Typed model for market-related UI state."""

    token_cap: float = Field(gt=0, description="Total permits available (Q)")

    model_config = ConfigDict(frozen=False)


class UIScenarioState(BaseModel):
    """Typed root model for entire UI scenario configuration.

    Replaces bare UIConfig class. Each field is a nested model for better organization.
    """

    # --- General ---
    n_agents: int = Field(DEFAULT_SCENARIO_N_AGENTS, gt=0)
    steps: int = Field(DEFAULT_SCENARIO_STEPS, gt=0)
    seed: int | None = None
    selected_scenario: str = "Custom"

    # --- Sub-configurations ---
    audit: UIAuditState = Field(default_factory=UIAuditState)
    market: UIMarketState = Field(default_factory=lambda: UIMarketState(token_cap=5))
    lab: UILabState = Field(default_factory=UILabState)

    model_config = ConfigDict(frozen=False)

    def to_scenario_config(self) -> ScenarioConfig:
        """Convert UI state to validated ScenarioConfig for simulation."""
        return ScenarioConfig(
            name=self.selected_scenario,
            n_agents=self.n_agents,
            steps=self.steps,
            audit=AuditConfig(
                base_prob=self.audit.base_prob,
                high_prob=self.audit.high_prob,
                false_positive_rate=self.audit.false_positive_rate,
                false_negative_rate=self.audit.false_negative_rate,
                penalty_amount=self.audit.penalty,
                backcheck_prob=self.audit.backcheck_prob,
                cost=self.audit.cost,
            ),
            market=MarketConfig(token_cap=self.market.token_cap),
            lab=LabConfig(
                economic_value_min=self.lab.economic_value_min,
                economic_value_max=self.lab.economic_value_max,
                risk_profile_min=self.lab.risk_profile_min,
                risk_profile_max=self.lab.risk_profile_max,
                capacity_min=self.lab.capacity_min,
                capacity_max=self.lab.capacity_max,
                capability_value=self.lab.capability_value,
                racing_factor=self.lab.racing_factor,
                reputation_sensitivity=self.lab.reputation_sensitivity,
                audit_coefficient=self.lab.audit_coefficient,
            ),
            seed=self.seed,
        )

    @classmethod
    def from_scenario_config(cls, config: ScenarioConfig) -> "UIScenarioState":
        """Create UI state from a ScenarioConfig."""
        return cls(
            n_agents=config.n_agents,
            steps=config.steps,
            seed=config.seed,
            selected_scenario=config.name,
            audit=UIAuditState(
                base_prob=config.audit.base_prob,
                high_prob=config.audit.high_prob,
                false_positive_rate=config.audit.false_positive_rate,
                false_negative_rate=config.audit.false_negative_rate,
                penalty=config.audit.penalty_amount,
                backcheck_prob=config.audit.backcheck_prob,
                cost=config.audit.cost,
            ),
            market=UIMarketState(token_cap=config.market.token_cap),
            lab=UILabState(
                economic_value_min=config.lab.economic_value_min,
                economic_value_max=config.lab.economic_value_max,
                risk_profile_min=config.lab.risk_profile_min,
                risk_profile_max=config.lab.risk_profile_max,
                capacity_min=config.lab.capacity_min,
                capacity_max=config.lab.capacity_max,
                capability_value=config.lab.capability_value,
                racing_factor=config.lab.racing_factor,
                reputation_sensitivity=config.lab.reputation_sensitivity,
                audit_coefficient=config.lab.audit_coefficient,
            ),
        )
