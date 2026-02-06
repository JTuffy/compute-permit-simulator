"""UI Configuration state - reactive parameters bound to sidebar controls.

This module wraps Pydantic models (UIAuditState, UILabState, UIMarketState, UIScenarioState)
with Solara reactivity to provide a clean, typed state management layer.
No more bare .reactive() calls without types.
"""

import solara

from compute_permit_sim.schemas import (
    ScenarioConfig,
    UIAuditState,
    UILabState,
    UIMarketState,
    UIScenarioState,
)


class UIConfig:
    """Reactive UI configuration parameters.

    This class wraps UIScenarioState (Pydantic model) with Solara reactivity.
    Each field is now strongly typed via the Pydantic models.
    """

    def __init__(self):
        # Initialize with default UIScenarioState, then wrap in reactive
        self._state: solara.Reactive[UIScenarioState] = solara.reactive(
            UIScenarioState()
        )

        # Expose individual reactive fields for backward compatibility with
        # existing UI bindings (sidebar controls)
        self.n_agents = solara.reactive(UIScenarioState().n_agents)
        self.steps = solara.reactive(UIScenarioState().steps)

        # Market
        self.token_cap = solara.reactive(UIScenarioState().market.token_cap)

        # Audit
        self.base_prob = solara.reactive(UIScenarioState().audit.base_prob)
        self.high_prob = solara.reactive(UIScenarioState().audit.high_prob)
        self.signal_fpr = solara.reactive(UIScenarioState().audit.false_positive_rate)
        self.signal_tpr = solara.reactive(
            1.0 - UIScenarioState().audit.false_negative_rate
        )  # TPR = 1 - FNR
        self.penalty = solara.reactive(UIScenarioState().audit.penalty)
        self.backcheck_prob = solara.reactive(UIScenarioState().audit.backcheck_prob)
        self.audit_cost = solara.reactive(UIScenarioState().audit.cost)

        # Lab Ranges
        self.economic_value_min = solara.reactive(
            UIScenarioState().lab.economic_value_min
        )
        self.economic_value_max = solara.reactive(
            UIScenarioState().lab.economic_value_max
        )
        self.risk_profile_min = solara.reactive(UIScenarioState().lab.risk_profile_min)
        self.risk_profile_max = solara.reactive(UIScenarioState().lab.risk_profile_max)
        self.capacity_min = solara.reactive(UIScenarioState().lab.capacity_min)
        self.capacity_max = solara.reactive(UIScenarioState().lab.capacity_max)

        # Lab Coefficients
        self.capability_value = solara.reactive(UIScenarioState().lab.capability_value)
        self.racing_factor = solara.reactive(UIScenarioState().lab.racing_factor)
        self.reputation_sensitivity = solara.reactive(
            UIScenarioState().lab.reputation_sensitivity
        )
        self.audit_coefficient = solara.reactive(
            UIScenarioState().lab.audit_coefficient
        )

        # Scenario Selection
        self.selected_scenario = solara.reactive("Custom")
        self.seed = solara.reactive(None)

    def get_ui_state(self) -> UIScenarioState:
        """Get the current complete UI state as a Pydantic model."""
        return UIScenarioState(
            n_agents=self.n_agents.value,
            steps=self.steps.value,
            seed=self.seed.value,
            selected_scenario=self.selected_scenario.value,
            audit=UIAuditState(
                base_prob=self.base_prob.value,
                high_prob=self.high_prob.value,
                false_positive_rate=self.signal_fpr.value,
                false_negative_rate=1.0 - self.signal_tpr.value,
                penalty=self.penalty.value,
                backcheck_prob=self.backcheck_prob.value,
                cost=self.audit_cost.value,
            ),
            market=UIMarketState(token_cap=float(self.token_cap.value)),
            lab=UILabState(
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

    def to_scenario_config(self) -> ScenarioConfig:
        """Convert reactive state to a validated ScenarioConfig."""
        ui_state = self.get_ui_state()
        return ui_state.to_scenario_config()

    def set_ui_state(self, state: UIScenarioState) -> None:
        """Apply a complete UIScenarioState to all reactive fields."""
        self.n_agents.value = state.n_agents
        self.steps.value = state.steps
        self.token_cap.value = state.market.token_cap
        self.seed.value = state.seed
        self.selected_scenario.value = state.selected_scenario

        # Audit
        self.base_prob.value = state.audit.base_prob
        self.high_prob.value = state.audit.high_prob
        self.signal_fpr.value = state.audit.false_positive_rate
        self.signal_tpr.value = 1.0 - state.audit.false_negative_rate
        self.penalty.value = state.audit.penalty
        self.backcheck_prob.value = state.audit.backcheck_prob
        self.audit_cost.value = state.audit.cost

        # Lab
        self.economic_value_min.value = state.lab.economic_value_min
        self.economic_value_max.value = state.lab.economic_value_max
        self.risk_profile_min.value = state.lab.risk_profile_min
        self.risk_profile_max.value = state.lab.risk_profile_max
        self.capacity_min.value = state.lab.capacity_min
        self.capacity_max.value = state.lab.capacity_max
        self.capability_value.value = state.lab.capability_value
        self.racing_factor.value = state.lab.racing_factor
        self.reputation_sensitivity.value = state.lab.reputation_sensitivity
        self.audit_coefficient.value = state.lab.audit_coefficient

    def from_scenario_config(self, config: ScenarioConfig) -> None:
        """Apply a ScenarioConfig to the reactive state."""
        ui_state = UIScenarioState.from_scenario_config(config)
        self.set_ui_state(ui_state)

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
        self.seed.value = config.seed


# Singleton instance
ui_config = UIConfig()
