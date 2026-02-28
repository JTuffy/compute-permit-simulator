"""UI Configuration state - reactive parameters bound to sidebar controls.

This module wraps Pydantic models (UIAuditState, UILabState, UIMarketState, UIScenarioState)
with Solara reactivity to provide a clean, typed state management layer.
No more bare .reactive() calls without types.
"""

import solara
from pydantic import BaseModel

from compute_permit_sim.schemas import ScenarioConfig


class UIConfig:
    """Reactive UI configuration parameters.

    Dynamically wraps ScenarioConfig with Solara reactivity.
    Flattens nested configuration fields into top-level reactive properties
    to match the expectations of AutoConfigView (which assumes flat UIConfig).
    """

    def __init__(self):
        # Initialize with defaults
        from compute_permit_sim.schemas import AuditConfig, LabConfig, MarketConfig

        default = ScenarioConfig(
            market=MarketConfig(permit_cap=20.0),
            audit=AuditConfig(),
            lab=LabConfig(),
        )

        # Special handling for Scenario metadata
        self.selected_scenario = solara.reactive("Custom")
        self.seed: solara.Reactive[int | None] = solara.reactive(
            None
        )  # Default to random

        # Recursively flatten and create reactive fields
        self._create_reactive_fields(default)

    def _create_reactive_fields(self, model: BaseModel):
        """Recursively create reactive attributes for all fields in the model."""
        for name, field in type(model).model_fields.items():
            value = getattr(model, name)

            # Recurse for sub-models (AuditConfig, MarketConfig, LabConfig)
            if isinstance(value, BaseModel):
                self._create_reactive_fields(value)
            else:
                # Leaf field - create reactive
                # Skip seed/name as they are handled specially or not fully reactive in the same way
                if name in ("seed", "name", "description"):
                    continue

                # Use setattr to create self.field_name = solara.reactive(value)
                # Assumes field names are unique across sub-configs (true for current schema)
                setattr(self, name, solara.reactive(value))

    def to_scenario_config(self) -> ScenarioConfig:
        """Convert reactive state to a validated ScenarioConfig."""
        # 1. Build a dict of all current reactive values
        # We need to reconstruct the nested structure

        def build_model(model_cls):
            data = {}
            for name, field in model_cls.model_fields.items():
                # Check if sub-model
                if isinstance(field.annotation, type) and issubclass(
                    field.annotation, BaseModel
                ):
                    data[name] = build_model(field.annotation)
                else:
                    # Leaf field
                    if name == "seed":
                        data[name] = self.seed.value
                    elif name == "name":
                        data[name] = self.selected_scenario.value
                    elif name == "description":
                        data[name] = ""  # Description not editable currently
                    elif hasattr(self, name):
                        val = getattr(self, name).value
                        # Ensure correct type (e.g. int vs float if Solara input returns string/float)
                        if field.annotation is int and val is not None:
                            try:
                                val = int(val)
                            except (ValueError, TypeError):
                                pass
                        data[name] = val
            return data

        # Reconstruct and validate
        config_dict = build_model(ScenarioConfig)
        return ScenarioConfig(**config_dict)

    def from_scenario_config(self, config: ScenarioConfig) -> None:
        """Apply a ScenarioConfig to the reactive state."""
        self.selected_scenario.value = config.name or "Custom"
        self.seed.value = config.seed

        def update_fields(model):
            for name, field in type(model).model_fields.items():
                value = getattr(model, name)

                if isinstance(value, BaseModel):
                    update_fields(value)
                else:
                    if name in ("seed", "name", "description"):
                        continue

                    if hasattr(self, name):
                        reactive_var = getattr(self, name)
                        reactive_var.value = value

        update_fields(config)


# Singleton instance
ui_config = UIConfig()
