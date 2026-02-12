import solara
import solara.lab

from compute_permit_sim.services import engine
from compute_permit_sim.vis.state.active import active_sim
from compute_permit_sim.vis.state.config import ui_config


@solara.component
def SimulationController():
    """Invisible component to handle the play loop."""
    # Using raise_error=False to gracefully handle Python 3.13 asyncio race conditions
    solara.lab.use_task(
        engine.play_loop,
        dependencies=[active_sim.state.value.is_playing],
        raise_error=False,
    )
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

        from compute_permit_sim.schemas import UrlConfig

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

            # Parse and validate strictly
            url_config = UrlConfig(**config_dict)

            # Apply to UI Config
            if url_config.n_agents is not None:
                ui_config.n_agents.value = url_config.n_agents
            if url_config.steps is not None:
                ui_config.steps.value = url_config.steps
            if url_config.token_cap is not None:
                ui_config.token_cap.value = url_config.token_cap
            if url_config.seed is not None:
                ui_config.seed.value = url_config.seed

            # Audit
            if url_config.penalty is not None:
                ui_config.penalty.value = url_config.penalty
            if url_config.base_prob is not None:
                ui_config.base_prob.value = url_config.base_prob
            if url_config.high_prob is not None:
                ui_config.high_prob.value = url_config.high_prob
            if url_config.signal_fpr is not None:
                ui_config.signal_fpr.value = url_config.signal_fpr
            if url_config.signal_tpr is not None:
                ui_config.signal_tpr.value = url_config.signal_tpr
            if url_config.backcheck_prob is not None:
                ui_config.backcheck_prob.value = url_config.backcheck_prob
            if url_config.audit_cost is not None:
                ui_config.audit_cost.value = url_config.audit_cost

            # Lab
            if url_config.ev_min is not None:
                ui_config.economic_value_min.value = url_config.ev_min
            if url_config.ev_max is not None:
                ui_config.economic_value_max.value = url_config.ev_max
            if url_config.risk_min is not None:
                ui_config.risk_profile_min.value = url_config.risk_min
            if url_config.risk_max is not None:
                ui_config.risk_profile_max.value = url_config.risk_max
            if url_config.cap_min is not None:
                ui_config.capacity_min.value = url_config.cap_min
            if url_config.cap_max is not None:
                ui_config.capacity_max.value = url_config.cap_max
            if url_config.vb is not None:
                ui_config.capability_value.value = url_config.vb
            if url_config.cr is not None:
                ui_config.racing_factor.value = url_config.cr
            if url_config.rep is not None:
                ui_config.reputation_sensitivity.value = url_config.rep
            if url_config.audit_coeff is not None:
                ui_config.audit_coefficient.value = url_config.audit_coeff

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
