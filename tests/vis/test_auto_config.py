import os
import sys

import solara
from pydantic import BaseModel, Field

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from compute_permit_sim.vis.components import AutoConfigView


class DummyConfig(BaseModel):
    name: str = "test"
    val: int = Field(10, json_schema_extra={"ui_group": "Group1", "ui_label": "Value"})
    min_val: float = Field(0.0, json_schema_extra={"ui_component": "range_min"})
    max_val: float = Field(1.0, json_schema_extra={"ui_component": "range_max"})


def test_auto_config_view_instantiation():
    # Just render it and check if it errors
    config = DummyConfig()

    # Readonly mode
    # This just executes the component function, Solara components are functions.
    # It might create Solara elements but without context it won't render to DOM.
    # But it validates logic inside AutoConfigView (parsing schema, etc).
    AutoConfigView(schema=DummyConfig, model=config, readonly=True)

    # Editable mode
    class MockUIConfig:
        name = solara.Reactive("test")
        val = solara.Reactive(10)
        min_val = solara.Reactive(0.0)
        max_val = solara.Reactive(1.0)

    ui_config = MockUIConfig()
    AutoConfigView(schema=DummyConfig, model=ui_config, readonly=False)
