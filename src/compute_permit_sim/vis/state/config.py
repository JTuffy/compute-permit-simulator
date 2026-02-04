"""UI Configuration state - reactive parameters bound to sidebar controls."""

import solara

from compute_permit_sim.schemas import (
    AuditConfig,
    LabConfig,
    MarketConfig,
    ScenarioConfig,
)


class UIConfig:
    """Reactive UI configuration parameters.

    This class holds all the reactive state for configuration sliders/inputs
    in the sidebar. It provides methods to convert to/from ScenarioConfig.
    """

    def __init__(self):
        # --- General ---
        self.n_agents = solara.reactive(5)
        self.steps = solara.reactive(5)

        # --- Market ---
        self.token_cap = solara.reactive(5)

        # --- Audit ---
        self.base_prob = solara.reactive(0.1)
        self.high_prob = solara.reactive(0.1)
        self.signal_fpr = solara.reactive(0.1)
        self.signal_tpr = solara.reactive(0.9)  # Maps to 1 - FNR
        self.penalty = solara.reactive(0.5)
        self.backcheck_prob = solara.reactive(0.0)

        # --- Lab Ranges ---
        self.economic_value_min = solara.reactive(0.5)
        self.economic_value_max = solara.reactive(1.5)
        self.risk_profile_min = solara.reactive(0.8)
        self.risk_profile_max = solara.reactive(1.2)
        self.capacity_min = solara.reactive(1.0)
        self.capacity_max = solara.reactive(2.0)

        # --- Lab Coefficients ---
        self.capability_value = solara.reactive(0.0)
        self.racing_factor = solara.reactive(1.0)
        self.reputation_sensitivity = solara.reactive(0.0)
        self.audit_coefficient = solara.reactive(1.0)

        # --- Scenario Selection ---
        self.selected_scenario = solara.reactive("Custom")
        self.seed = solara.reactive(None)

    def to_scenario_config(self) -> ScenarioConfig:
        """Convert reactive state to a validated ScenarioConfig."""
        return ScenarioConfig(
            name=self.selected_scenario.value,
            n_agents=self.n_agents.value,
            steps=self.steps.value,
            audit=AuditConfig(
                base_prob=self.base_prob.value,
                high_prob=self.high_prob.value,
                false_positive_rate=self.signal_fpr.value,
                false_negative_rate=1.0 - self.signal_tpr.value,
                penalty_amount=self.penalty.value,
                backcheck_prob=self.backcheck_prob.value,
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
            seed=self.seed.value,
        )

    def from_scenario_config(self, config: ScenarioConfig) -> None:
        """Apply a ScenarioConfig to the reactive state."""
        # Top Level
        self.n_agents.value = config.n_agents
        self.steps.value = config.steps
        self.token_cap.value = config.market.token_cap

        # Audit
        self.base_prob.value = config.audit.base_prob
        self.high_prob.value = config.audit.high_prob
        self.signal_fpr.value = config.audit.false_positive_rate
        self.signal_tpr.value = 1.0 - config.audit.false_negative_rate
        self.penalty.value = config.audit.penalty_amount
        self.backcheck_prob.value = config.audit.backcheck_prob

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
