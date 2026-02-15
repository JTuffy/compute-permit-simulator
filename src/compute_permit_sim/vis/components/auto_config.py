from typing import Any, Dict, List, Set, Type

import solara
from pydantic import BaseModel

from compute_permit_sim.vis.components.controls import RangeController, RangeView


@solara.component
def AutoConfigView(
    schema: Type[BaseModel],
    model: Any | None = None,
    readonly: bool = False,
    collapsible: bool = False,
    render_mode: str | None = None,
    exclude: List[str] | None = None,
):
    """
    Automatically render a configuration view based on a Pydantic schema.

    Args:
        schema: The Pydantic model class (e.g. ScenarioConfig).
        model: The data source.
               - If readonly=True, this should be a Pydantic model instance (e.g. run.config).
               - If readonly=False, this should be the UIConfig object (reactive).
        readonly: Whether controls are read-only views.
        collapsible: Whether to wrap groups in collapsible details (for dense views).
        render_mode: "tabs" to use Tabs, None for Cards.
        exclude: List of field names to exclude from rendering.
    """

    # 1. Parse Schema & Group Fields
    # Structure: { "Group Name": [ (field_name, field_info, value_getter) ] }
    groups: Dict[str, List[Dict[str, Any]]] = {}

    def get_value(path: str, field_name: str):
        if model is None:
            return None

        if readonly:
            # Nested Pydantic model: e.g. model.audit.penalty_amount
            # path is like "audit.", field_name "penalty_amount"
            obj = model
            if path:
                for part in path.rstrip(".").split("."):
                    obj = getattr(obj, part, None)
                    if obj is None:
                        return None
            return getattr(obj, field_name, None)
        else:
            # Flat UIConfig: e.g. model.penalty_amount
            # heuristic: match leaf name
            return getattr(model, field_name, None)

    def process_model(model_cls, path=""):
        for name, info in model_cls.model_fields.items():
            if exclude and name in exclude:
                continue

            # Special case: Seed is rendered manually at the top, so skip it here
            if name == "seed":
                continue

            # Check if sub-model
            if isinstance(info.annotation, type) and issubclass(
                info.annotation, BaseModel
            ):
                process_model(info.annotation, path + name + ".")
                continue

            # It's a leaf field
            extra = info.json_schema_extra or {}
            group = extra.get("ui_group", "General")

            if group not in groups:
                groups[group] = []

            groups[group].append(
                {"name": name, "info": info, "path": path, "extra": extra}
            )

    process_model(schema)

    # 2. Render Groups
    # specific order
    preferred_order = [
        "General",
        "Audit Policy",
        "Market",
        "Lab Generation",
        "Dynamic Factors",
    ]
    sorted_group_names = sorted(
        groups.keys(),
        key=lambda g: preferred_order.index(g) if g in preferred_order else 99,
    )

    # 2. Render Groups Container
    with solara.Column(gap="0px"):
        # Explicitly render Seed at top if it exists and is not excluded
        # Seed is special because it's on the root config but often wanted at top
        if not readonly and (not exclude or "seed" not in exclude):
            # Try to get seed from model.seed if available
            seed_val = getattr(model, "seed", None)
            if seed_val is not None:
                # If reactive
                if isinstance(seed_val, solara.Reactive):

                    def set_seed(v):
                        if v == "" or v is None:
                            seed_val.value = None
                        else:
                            try:
                                seed_val.value = int(v)
                            except ValueError:
                                pass

                    solara.InputText(
                        label="Random Seed (Optional)",
                        value=str(seed_val.value) if seed_val.value is not None else "",
                        on_value=set_seed,
                        dense=True,
                        disabled=readonly,
                    )
                else:
                    # Readonly int
                    solara.InputInt(
                        label="Random Seed", value=seed_val, dense=True, disabled=True
                    )

        # Helper to render content of a group
        def render_group_content(items):
            processed: Set[str] = set()

            for item in items:
                name = item["name"]
                if name in processed:
                    continue

                extra = item["extra"]
                component_type = extra.get("ui_component")

                # Handle Range Pairs
                if component_type == "range_min":
                    # Find corresponding max
                    base = name[:-4]  # strip _min
                    max_name = base + "_max"
                    # find item for max_name
                    max_item = next((i for i in items if i["name"] == max_name), None)

                    if max_item:
                        processed.add(name)
                        processed.add(max_name)

                        val_min = get_value(item["path"], name)
                        val_max = get_value(max_item["path"], max_name)
                        label = extra.get("ui_label", name).replace(" Min", "")

                        if readonly:
                            # Ensure values are not None
                            if val_min is not None and val_max is not None:
                                RangeView(label, val_min, val_max)
                        else:
                            if val_min is not None and val_max is not None:
                                RangeController(label, val_min, val_max)
                        continue

                if component_type == "range_max":
                    # Should have been handled by range_min
                    continue

                # Standard Fields
                processed.add(name)
                val = get_value(item["path"], name)
                label = extra.get("ui_label", name)
                fmt = extra.get("ui_format", "float")

                # disable if readonly
                disabled = readonly

                # Determine if reactive
                is_reactive = isinstance(val, solara.Reactive)
                current_val = val.value if is_reactive else val

                # Define setter locally to capture 'val' correctly
                def make_setter(target_reactive, caster):
                    def _setter(v):
                        if v == "" or v is None:
                            target_reactive.value = None
                        else:
                            try:
                                target_reactive.value = caster(v)
                            except ValueError:
                                pass

                    return _setter

                # Render based on type/format
                if fmt == "percent":
                    if not readonly and is_reactive:
                        solara.InputFloat(
                            label=label,
                            value=val,
                            dense=True,
                            disabled=disabled,
                        )
                    else:
                        if current_val is not None:
                            solara.InputFloat(
                                label=label,
                                value=current_val,
                                dense=True,
                                disabled=True,
                            )

                elif fmt == "int" or (
                    # If it's an int field but value might be None (like seed)
                    not fmt and isinstance(current_val, (int, type(None)))
                ):
                    # Handle int inputs that might be None
                    if not readonly and is_reactive:
                        solara.InputText(
                            label=label,
                            value=str(current_val) if current_val is not None else "",
                            on_value=make_setter(val, int),
                            dense=True,
                            disabled=disabled,
                        )
                    else:
                        if current_val is not None:
                            solara.InputInt(
                                label=label,
                                value=current_val,
                                dense=True,
                                disabled=True,
                            )

                elif isinstance(current_val, bool):
                    if not readonly and is_reactive:
                        solara.Checkbox(label=label, value=val, disabled=disabled)
                    else:
                        # For readonly bool, checkbox is fine
                        solara.Checkbox(label=label, value=current_val, disabled=True)

                else:  # float, currency, scientific
                    if not readonly and is_reactive:
                        solara.InputText(
                            label=label,
                            value=str(current_val) if current_val is not None else "",
                            on_value=make_setter(val, float),
                            dense=True,
                            disabled=disabled,
                        )
                    else:
                        if current_val is not None:
                            solara.InputFloat(
                                label=label,
                                value=current_val,
                                dense=True,
                                disabled=True,
                            )

        # Render all groups vertically
        for group_name in sorted_group_names:
            # Add a subtle separator/header
            solara.Markdown(
                f"**{group_name}**",
                style="font-size: 0.85rem; opacity: 0.6; margin-top: 12px; margin-bottom: 4px; text-transform: uppercase;",
            )
            render_group_content(groups[group_name])
