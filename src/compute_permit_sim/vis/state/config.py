"""UI Configuration state - reactive parameters bound to sidebar controls.

This module wraps Pydantic models (UIAuditState, UILabState, UIMarketState, UIScenarioState)
with Solara reactivity to provide a clean, typed state management layer.
No more bare .reactive() calls without types.
"""

import solara

from compute_permit_sim.schemas import (
    AuditConfig,
    LabConfig,
    MarketConfig,
    ScenarioConfig,
)


class UIConfig:
    """Reactive UI configuration parameters.

    This class wraps UIScenarioState (Pydantic model) with Solara reactivity.
    Each field is now strongly typed via the Pydantic models.
    """

    def __init__(self):
        # Initialize with defaults from ScenarioConfig
        default = ScenarioConfig(
            market=MarketConfig(token_cap=5), audit=AuditConfig(), lab=LabConfig()
        )

        self.n_agents = solara.reactive(default.n_agents)
        self.steps = solara.reactive(default.steps)

        # Market
        self.token_cap = solara.reactive(default.market.token_cap)

        # Audit
        self.base_prob = solara.reactive(default.audit.base_prob)
        self.high_prob = solara.reactive(default.audit.high_prob)
        self.signal_fpr = solara.reactive(default.audit.false_positive_rate)
        self.signal_tpr = solara.reactive(
            1.0 - default.audit.false_negative_rate
        )  # TPR = 1 - FNR
        self.penalty = solara.reactive(default.audit.penalty_amount)
        self.backcheck_prob = solara.reactive(default.audit.backcheck_prob)
        self.audit_cost = solara.reactive(default.audit.cost)

        # Lab Ranges
        self.economic_value_min = solara.reactive(default.lab.economic_value_min)
        self.economic_value_max = solara.reactive(default.lab.economic_value_max)
        self.risk_profile_min = solara.reactive(default.lab.risk_profile_min)
        self.risk_profile_max = solara.reactive(default.lab.risk_profile_max)
        self.capacity_min = solara.reactive(default.lab.capacity_min)
        self.capacity_max = solara.reactive(default.lab.capacity_max)

        # Lab Coefficients
        self.capability_value = solara.reactive(default.lab.capability_value)
        self.racing_factor = solara.reactive(default.lab.racing_factor)
        self.reputation_sensitivity = solara.reactive(
            default.lab.reputation_sensitivity
        )
        self.audit_coefficient = solara.reactive(default.lab.audit_coefficient)

        # Scenario Selection
        self.selected_scenario = solara.reactive("Custom")
        self.seed = solara.reactive(None)

    def to_scenario_config(self) -> ScenarioConfig:
        """Convert reactive state to a validated ScenarioConfig."""
        return ScenarioConfig(
            n_agents=self.n_agents.value,
            steps=self.steps.value,
            seed=self.seed.value,
            name=self.selected_scenario.value,
            audit=AuditConfig(
                base_prob=self.base_prob.value,
                high_prob=self.high_prob.value,
                false_positive_rate=self.signal_fpr.value,
                false_negative_rate=1.0 - self.signal_tpr.value,
                penalty_amount=self.penalty.value,
                backcheck_prob=self.backcheck_prob.value,
                cost=self.audit_cost.value,
            ),
            market=MarketConfig(token_cap=float(self.token_cap.value)),
            lab=LabConfig(
                economic_value_min=self.economic_value_min.value,
                economic_value_max=self.economic_value_max.value,
                risk_profile_min=self.risk_profile_min.value,
                risk_profile_max=self.risk_profile_max.value,
                capacity_min=self.capacity_min.value,
                capacity_max=self.capacity_max.value,
                capability_value=self.capability_value.value,
                racing_factor=self.racing_factor.value,
                reputation_sensitivity=self.reputation_sensitivity.value,
                audit_coefficient=self.audit_coefficient.value,
            ),
        )

    def from_scenario_config(self, config: ScenarioConfig) -> None:
        """Apply a ScenarioConfig to the reactive state."""
        self.n_agents.value = config.n_agents
        self.steps.value = config.steps
        self.token_cap.value = config.market.token_cap
        self.seed.value = config.seed
        self.selected_scenario.value = config.name

        # Audit
        self.base_prob.value = config.audit.base_prob
        self.high_prob.value = config.audit.high_prob
        self.signal_fpr.value = config.audit.false_positive_rate
        self.signal_tpr.value = 1.0 - config.audit.false_negative_rate
        self.penalty.value = config.audit.penalty_amount
        self.backcheck_prob.value = config.audit.backcheck_prob
        self.audit_cost.value = config.audit.cost

        # Lab
        self.economic_value_min.value = config.lab.economic_value_min
        self.economic_value_max.value = config.lab.economic_value_max
        self.risk_profile_min.value = config.lab.risk_profile_min
        self.risk_profile_max.value = config.lab.risk_profile_max
        self.capacity_min.value = config.lab.capacity_min
        self.capacity_max.value = config.lab.capacity_max
        self.capability_value.value = config.lab.capability_value
        self.racing_factor.value = config.lab.racing_factor
        self.reputation_sensitivity.value = config.lab.reputation_sensitivity
        self.audit_coefficient.value = config.lab.audit_coefficient


# Singleton instance
ui_config = UIConfig()
