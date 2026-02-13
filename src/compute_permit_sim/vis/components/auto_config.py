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

    with solara.Column():
        for group_name in sorted_group_names:
            items = groups[group_name]

            # Helper to render content of a group
            # We must define it inline to capture `items` closure correctly in loop?
            # Actually better to just render inline.

            def render_group_content(items=items):
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
                        max_item = next(
                            (i for i in items if i["name"] == max_name), None
                        )

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

                    # If val is missing (e.g. not in UIConfig), skip or show placeholder
                    if val is None:
                        continue

                    # Determine if reactive
                    is_reactive = isinstance(val, solara.Reactive)
                    current_val = val.value if is_reactive else val

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
                            solara.InputFloat(
                                label=label,
                                value=current_val,
                                dense=True,
                                disabled=True,
                            )

                    elif fmt == "int":
                        if not readonly and is_reactive:
                            solara.InputInt(
                                label=label,
                                value=val,
                                dense=True,
                                disabled=disabled,
                            )
                        else:
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
                            solara.Checkbox(
                                label=label, value=current_val, disabled=True
                            )

                    else:  # float, currency, scientific
                        if not readonly and is_reactive:
                            solara.InputFloat(
                                label=label,
                                value=val,
                                dense=True,
                                disabled=disabled,
                            )
                        else:
                            solara.InputFloat(
                                label=label,
                                value=current_val,
                                dense=True,
                                disabled=True,
                            )

            if collapsible:
                with solara.Details(summary=group_name):
                    with solara.Column(
                        style="padding-left: 10px; border-left: 2px solid #eee;"
                    ):
                        render_group_content()
            else:
                with solara.Card(group_name, style="margin-bottom: 6px;"):
                    with solara.Column():
                        render_group_content()
