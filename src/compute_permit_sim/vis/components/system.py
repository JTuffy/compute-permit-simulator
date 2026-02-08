import solara
import solara.lab

from compute_permit_sim.schemas import UrlConfig
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
    """Manages synchronization between UI Config and URL via a unique 'id'.

    The 'id' URL parameter is a Base64 encoded JSON string of the entire configuration.
    """
    router = solara.use_router()

    def read_url():
        import base64
        import json
        from urllib.parse import parse_qs

        query = router.search
        if not query:
            return

        if query.startswith("?"):
            query = query[1:]

        data = parse_qs(query)

        # Look for Base64 'id'
        if "id" in data:
            try:
                encoded_id = data["id"][0]
                # Fallback URL safe decoding if needed, but standard b64decode usually fine
                # We expect simple base64
                json_str = base64.b64decode(encoded_id).decode("utf-8")
                config_dict = json.loads(json_str)

                # Parse and Validate strictly
                url_config = UrlConfig(**config_dict)

                # Apply to UI Config safely
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
                base64.binascii.Error,
                json.JSONDecodeError,
                ImportError,
                AttributeError,
            ):
                pass

    # We only run this once on mount
    solara.use_effect(read_url, [])

    # --- WRITE: Update URL 'id' when ANY Config Changes ---

    # Collect all dependencies for the effect
    deps = [
        ui_config.n_agents.value,
        ui_config.steps.value,
        ui_config.token_cap.value,
        ui_config.seed.value,
        ui_config.penalty.value,
        ui_config.base_prob.value,
        ui_config.high_prob.value,
        ui_config.signal_fpr.value,
        ui_config.signal_tpr.value,
        ui_config.signal_tpr.value,
        ui_config.backcheck_prob.value,
        ui_config.audit_cost.value,
        ui_config.economic_value_min.value,
        ui_config.economic_value_max.value,
        ui_config.risk_profile_min.value,
        ui_config.risk_profile_max.value,
        ui_config.capacity_min.value,
        ui_config.capacity_max.value,
        ui_config.capability_value.value,
        ui_config.racing_factor.value,
        ui_config.reputation_sensitivity.value,
        ui_config.audit_coefficient.value,
    ]

    async def write_url():
        # Debounce: Wait for 300ms of inactivity before updating URL
        # This prevents 20+ updates when loading a scenario
        import asyncio

        await asyncio.sleep(0.3)

        import base64
        import json

        # Serialize Current State strictly via Schema
        current_state = UrlConfig(
            n_agents=ui_config.n_agents.value,
            steps=ui_config.steps.value,
            token_cap=ui_config.token_cap.value,
            seed=ui_config.seed.value,
            penalty=ui_config.penalty.value,
            base_prob=ui_config.base_prob.value,
            high_prob=ui_config.high_prob.value,
            signal_fpr=ui_config.signal_fpr.value,
            signal_tpr=ui_config.signal_tpr.value,
            backcheck_prob=ui_config.backcheck_prob.value,
            audit_cost=ui_config.audit_cost.value,
            ev_min=ui_config.economic_value_min.value,
            ev_max=ui_config.economic_value_max.value,
            risk_min=ui_config.risk_profile_min.value,
            risk_max=ui_config.risk_profile_max.value,
            cap_min=ui_config.capacity_min.value,
            cap_max=ui_config.capacity_max.value,
            vb=ui_config.capability_value.value,
            cr=ui_config.racing_factor.value,
            rep=ui_config.reputation_sensitivity.value,
            audit_coeff=ui_config.audit_coefficient.value,
        ).model_dump(exclude_none=True)

        # Encode to Base64 ID
        json_bytes = json.dumps(current_state).encode("utf-8")
        encoded_id = base64.b64encode(json_bytes).decode("utf-8")

        # Push to URL
        new_search = f"?id={encoded_id}"
        if router.search != new_search:
            router.push(new_search)

    solara.lab.use_task(write_url, dependencies=deps)

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
