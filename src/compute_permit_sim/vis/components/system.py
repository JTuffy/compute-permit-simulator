import solara
import solara.lab

from compute_permit_sim.vis.state.config import ui_config


@solara.component
def SimulationController():
    """Invisible component — previously drove the async play loop.

    The play loop has been replaced by a headless background thread launched
    directly from SimulationEngine.start_run().  This component is kept as
    a no-op stub so app.py import sites remain stable.
    """
    return solara.Div(style="display: none;")


@solara.component
def UrlManager():
    """Reads config from URL on page load via the 'id' query parameter.

    The 'id' is a Base64-encoded JSON string of a UrlConfig, generated
    by pack_current_run() after a simulation completes.  This component
    only reads — it never pushes updates back to the URL.
    """
    router = solara.use_router()

    def read_url():
        import base64
        import json
        from urllib.parse import parse_qs

        from compute_permit_sim.schemas import ScenarioConfig

        query = router.search
        if not query:
            return

        if query.startswith("?"):
            query = query[1:]

        data = parse_qs(query)

        if "id" not in data:
            return

        try:
            encoded_id = data["id"][0]
            json_str = base64.b64decode(encoded_id).decode("utf-8")
            config_dict = json.loads(json_str)

            # Validate and reconstruct ScenarioConfig
            # Missing fields in JSON (due to exclude_defaults) will use defaults from schema
            loaded_config = ScenarioConfig(**config_dict)

            # Apply to UI Config
            ui_config.from_scenario_config(loaded_config)

        except (
            ValueError,
            TypeError,
            json.JSONDecodeError,
            ImportError,
            AttributeError,
        ):
            pass

    # Run once on mount
    solara.use_effect(read_url, [])

    return solara.Div(style="display: none;")


@solara.component
def KeyboardListener():
    """Global keyboard shortcut listener.

    Since global window events are hard in Solara, we attach key listeners to the
    main UI container in layout/main.py. This component is effectively a placeholder
    for logic if we were using ipyevents.

    For now, we will handle keys in the root Page container by setting it to focusable.
    """
    return solara.Div(style="display: none;")
