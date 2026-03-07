"""UI Configuration state - reactive parameters bound to sidebar controls.

Wraps ScenarioConfig with Solara reactivity to drive sidebar controls.
Flattens nested config fields (AuditConfig, MarketConfig, LabConfig) into
top-level reactive attributes so AutoConfigView can address them uniformly.

Design note:
  Field names are collected into ``_reactive_field_names`` at init time.
  All runtime field lookups go through this set, so a renamed schema field
  raises a KeyError immediately at startup rather than silently producing
  wrong values.
"""

import solara
from pydantic import BaseModel

from compute_permit_sim.schemas import ScenarioConfig

# Fields handled explicitly in to/from_scenario_config — NOT stored as reactive attrs
_SPECIAL_FIELDS: frozenset[str] = frozenset({"seed", "name", "description", "notes"})


class UIConfig:
    """Reactive UI configuration parameters.

    Each leaf field in ScenarioConfig (except the special-cased metadata
    fields) becomes a ``solara.Reactive`` attribute on this object.
    ``_reactive_field_names`` is the authoritative set of those field names.
    """

    def __init__(self) -> None:
        from compute_permit_sim.schemas import AuditConfig, LabConfig, MarketConfig

        default = ScenarioConfig(
            market=MarketConfig(permit_cap=20.0),
            audit=AuditConfig(),
            lab=LabConfig(),
        )

        # Metadata handled separately
        self.selected_scenario: solara.Reactive[str] = solara.reactive("Custom")
        self.notes: solara.Reactive[str] = solara.reactive("")
        self.seed: solara.Reactive[int | None] = solara.reactive(None)

        # Build the registry and reactive attrs in one pass
        self._reactive_field_names: frozenset[str] = frozenset(
            self._create_reactive_fields(default)
        )

    def _create_reactive_fields(self, model: BaseModel) -> list[str]:
        """Recursively create reactive attributes; return names of created fields."""
        created: list[str] = []
        for name in type(model).model_fields:
            value = getattr(model, name)
            if isinstance(value, BaseModel):
                created.extend(self._create_reactive_fields(value))
            elif name not in _SPECIAL_FIELDS:
                setattr(self, name, solara.reactive(value))
                created.append(name)
        return created

    def to_scenario_config(self) -> ScenarioConfig:
        """Convert reactive state to a validated ScenarioConfig."""

        def build_model(model_cls: type[BaseModel]) -> dict:
            data: dict = {}
            for name, field in model_cls.model_fields.items():
                annotation = field.annotation
                if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                    data[name] = build_model(annotation)
                elif name == "seed":
                    data[name] = self.seed.value
                elif name == "name":
                    data[name] = self.selected_scenario.value
                elif name == "description":
                    data[name] = ""  # Not editable in the current UI
                elif name == "notes":
                    data[name] = self.notes.value
                elif name in self._reactive_field_names:
                    val = getattr(self, name).value
                    # Coerce to int if schema expects it — Solara inputs return float
                    if annotation is int and val is not None:
                        try:
                            val = int(val)
                        except (ValueError, TypeError):
                            pass
                    data[name] = val
                else:
                    raise KeyError(
                        f"UIConfig: schema field '{name}' has no reactive attribute. "
                        "Update _SPECIAL_FIELDS or add explicit handling."
                    )
            return data

        return ScenarioConfig(**build_model(ScenarioConfig))

    def from_scenario_config(self, config: ScenarioConfig) -> None:
        """Apply a ScenarioConfig to the reactive state."""
        self.selected_scenario.value = config.name or "Custom"
        self.notes.value = config.notes
        self.seed.value = config.seed

        def update_fields(model: BaseModel) -> None:
            for name in type(model).model_fields:
                value = getattr(model, name)
                if isinstance(value, BaseModel):
                    update_fields(value)
                elif name not in _SPECIAL_FIELDS:
                    if name not in self._reactive_field_names:
                        raise KeyError(
                            f"UIConfig: schema field '{name}' has no reactive attribute. "
                            "Update _SPECIAL_FIELDS or add explicit handling."
                        )
                    getattr(self, name).value = value

        update_fields(config)


# Singleton instance
ui_config = UIConfig()
