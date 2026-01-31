import pandas as pd
import solara
import solara.lab

from compute_permit_sim.vis.state import manager

# --- Components ---


@solara.component
def SimulationController():
    """Invisible component to handle the play loop."""
    solara.lab.use_task(manager.play_loop, dependencies=[manager.is_playing.value])
    return solara.Div(style="display: none;")


@solara.component
def ParamView(config):
    """Read-only view of a ScenarioConfig."""
    with solara.lab.Tabs(vertical=True, align="left", dark=False):
        with solara.lab.Tab("General", style={"min-width": "auto"}):
            with solara.Column(gap="0px", style="opacity: 0.8; font-size: 0.9em;"):
                solara.InputInt(label="Steps", value=config.steps, disabled=True)
                solara.InputInt(label="N Agents", value=config.n_agents, disabled=True)
                solara.InputInt(
                    label="Token Cap (Q)",
                    value=int(config.market.token_cap),
                    disabled=True,
                )

        with solara.lab.Tab("Audit", style={"min-width": "auto"}):
            with solara.Column(gap="0px", style="opacity: 0.8; font-size: 0.9em;"):
                solara.InputFloat(
                    label="Penalty (P)",
                    value=config.audit.penalty_amount,
                    disabled=True,
                )
                solara.InputFloat(
                    label="Base Prob (pi_0)",
                    value=config.audit.base_prob,
                    disabled=True,
                )
                solara.InputFloat(
                    label="High Prob (pi_1)",
                    value=config.audit.high_prob,
                    disabled=True,
                )
                solara.InputFloat(
                    label="Signal TPR", value=config.audit.signal_tpr, disabled=True
                )
                solara.InputFloat(
                    label="Signal FPR", value=config.audit.signal_fpr, disabled=True
                )
                solara.InputInt(
                    label="Audit Budget (Count)",
                    value=config.audit.audit_budget,
                    disabled=True,
                )

        with solara.lab.Tab("Lab", style={"min-width": "auto"}):
            with solara.Column(gap="0px", style="opacity: 0.8; font-size: 0.9em;"):
                solara.Markdown("*Gross Value Range*")
                solara.InputFloat(
                    label="Min", value=config.lab.gross_value_min, disabled=True
                )
                solara.InputFloat(
                    label="Max", value=config.lab.gross_value_max, disabled=True
                )
                solara.Markdown("*Risk Profile Range*")
                solara.InputFloat(
                    label="Min", value=config.lab.risk_profile_min, disabled=True
                )
                solara.InputFloat(
                    label="Max", value=config.lab.risk_profile_max, disabled=True
                )


@solara.component
def RunHistoryList():
    if not manager.run_history.value:
        solara.Markdown("_No runs yet._")
        return

    # Compact list with custom items
    with solara.Column(gap="4px"):
        for run in manager.run_history.value:
            is_selected = (manager.selected_run.value is not None) and (
                manager.selected_run.value.id == run.id
            )
            bg_color = "#e0f2f1" if is_selected else "transparent"

            # Label generation
            if run.metrics:
                comp = run.metrics.get("final_compliance", 0)
                price = run.metrics.get("final_price", 0)
                try:
                    display_id = run.id.split("_")[1]
                except IndexError:
                    display_id = run.id
                label = f"{display_id} (C:{comp:.0%} ${price:.0f})"
            else:
                label = f"{run.id} ({len(run.steps)})"

            # Actions
            def load_config(r=run):
                manager.restore_config(r)

            def view_run(r=run):
                manager.selected_run.value = r

            # Rich Tooltip Construction
            # Parse ID for timestamp: YYYYMMDD_HHMMSS
            try:
                parts = run.id.split("_")
                ts_str = f"{parts[0]}-{parts[1]}"
            except IndexError:
                ts_str = "Unknown"

            c = run.config
            tooltip_text = (
                f"Run: {run.id}\n"
                f"Time: {ts_str}\n"
                f"cfg: {c.n_agents} agents, {c.steps} steps\n"
                f"Token Cap: {c.market.token_cap}, Budget: {c.audit.audit_budget}"
            )

            with solara.Row(
                style=(
                    f"background-color: {bg_color}; padding: 2px; align-items: center;"
                ),
                classes=["hover-bg"],
            ):
                # View Button (Main interaction)
                with solara.Tooltip(tooltip_text):
                    solara.Button(
                        label,
                        on_click=view_run,
                        text=True,
                        style="text-transform: none; text-align: left; flex-grow: 1;",
                        color="primary" if is_selected else None,
                    )

                # Load Config Button
                with solara.Tooltip("Load these parameters to Config Panel"):
                    solara.Button(
                        icon_name="mdi-upload",
                        on_click=load_config,
                        icon=True,
                        small=True,
                    )


@solara.component
def Dashboard():
    # Helper to get data source
    run = manager.selected_run.value
    is_live = run is None

    # Extract data
    step_count = manager.step_count.value if is_live else len(run.steps)

    price_series = (
        manager.price_history.value
        if is_live
        else [s.market.get("price", 0) for s in run.steps]
    )

    # Placeholder for compliance in history (if missed in schema)
    if not is_live:
        # Calculate compliance per step dynamically
        compliance_series = []
        for s in run.steps:
            compliant_count = sum(1 for a in s.agents if a.get("Compliant"))
            total = len(s.agents)
            compliance_series.append(compliant_count / total if total > 0 else 0)
    else:
        compliance_series = manager.compliance_history.value

    # Split Dashboard Logic
    if not is_live:
        solara.Markdown("### Run Analysis")
        with solara.Row():
            # Left: Locked Params
            with solara.Column(
                style=("width: 40%; padding-right: 20px; border-right: 1px solid #eee;")
            ):
                solara.Markdown("**Run Configuration**")
                ParamView(run.config)

            # Right: Results
            with solara.Column(style="width: 60%; padding-left: 20px;"):
                solara.Markdown("**Run Metrics**")
                # Reuse the metrics display logic here or inline it
                solara.Markdown(f"**Steps Taken:** {step_count}")

                current_compliance = "N/A"
                current_price = "N/A"
                if compliance_series:
                    current_compliance = f"{compliance_series[-1]:.2%}"
                if price_series:
                    current_price = f"{price_series[-1]:.2f}"

                with solara.Columns([1, 1]):
                    solara.Markdown(f"**Final Compliance:** {current_compliance}")
                    solara.Markdown(f"**Final Price:** {current_price}")

        # Graphs (Full Width Bottom)
        solara.Markdown("### Run Graphs")
        with solara.Columns([1, 1]):
            with solara.Column():
                if compliance_series:
                    from matplotlib.figure import Figure

                    fig = Figure(figsize=(6, 3))
                    ax = fig.subplots()
                    ax.plot(compliance_series, label="Compliance", color="green")
                    ax.set_ylim(-0.05, 1.05)
                    ax.legend()
                    ax.grid(True)
                    solara.FigureMatplotlib(fig)

            with solara.Column():
                if price_series:
                    from matplotlib.figure import Figure

                    fig = Figure(figsize=(6, 3))
                    ax = fig.subplots()
                    ax.plot(price_series, label="Price", color="blue")
                    ax.legend()
                    ax.grid(True)
                    solara.FigureMatplotlib(fig)

    else:
        # Live Monitoring View
        with solara.Card("Live Metrics"):
            solara.Markdown(f"**Step:** {step_count}")
            if compliance_series:
                solara.Markdown(f"**Current Compliance:** {compliance_series[-1]:.2%}")
            if price_series:
                solara.Markdown(f"**Current Price:** {price_series[-1]:.2f}")

        # Live Graphs
        with solara.Columns([1, 1]):
            # ... (existing graph code but condensed if needed)
            pass
            # For brevity, reusing the existing graph blocks below mostly unchanged,
            # but ensuring they only render if we are in live mode
            # or they are part of the 'else' block above.

        # Start existing graph block replication for Live Mode
        with solara.Columns([1, 1]):
            with solara.Column():
                if compliance_series:
                    from matplotlib.figure import Figure

                    fig = Figure(figsize=(6, 4))
                    ax = fig.subplots()
                    ax.plot(compliance_series, label="Compliance", color="green")
                    ax.set_ylim(-0.05, 1.05)
                    ax.legend()
                    ax.grid(True)
                    solara.FigureMatplotlib(fig)
                else:
                    solara.Markdown("No Data")

            with solara.Column():
                if price_series:
                    from matplotlib.figure import Figure

                    fig = Figure(figsize=(6, 4))
                    ax = fig.subplots()
                    ax.plot(price_series, label="Price", color="blue")
                    ax.legend()
                    ax.grid(True)
                    solara.FigureMatplotlib(fig)
                else:
                    solara.Markdown("No Data")


@solara.component
def InspectorTab():
    run = manager.selected_run.value
    is_live = run is None

    # Hook must be unconditional.
    # We use a key to reset state when the run ID changes.
    run_id = run.id if run else "live"
    step_idx, set_step_idx = solara.use_state(0, key=run_id)

    solara.Markdown(
        "### Step Inspector" + (" (Historical)" if not is_live else " (Live)")
    )

    # Flatten logic
    if is_live:
        price = manager.model.value.market.current_price if manager.model.value else 0
        supply = manager.model.value.market.max_supply if manager.model.value else 0
        n_agents = manager.model.value.n_agents if manager.model.value else 0
        agents_df = manager.agents_df.value
    else:
        # For history, use slider
        if len(run.steps) > 0:
            # Clamp
            idx = max(0, min(step_idx, len(run.steps) - 1))
            step = run.steps[idx]

            solara.SliderInt(
                label="Step View",
                value=step_idx,
                min=0,
                max=len(run.steps) - 1,
                on_value=set_step_idx,
            )

            price = step.market.get("price", 0)
            supply = step.market.get("supply", 0)
            n_agents = len(step.agents)
            agents_df = pd.DataFrame(step.agents)
        else:
            price = 0
            supply = 0
            n_agents = 0
            agents_df = None

    # Use existing components for display
    # Market Summary
    with solara.Card("Market Phase"):
        solara.Markdown(f"**Clearing Price:** {price:.2f}")
        solara.Markdown(f"**Permits Available:** {supply} / {n_agents}")

    # Agent Table
    if agents_df is not None:
        solara.Markdown("#### Agent Phase (Decisions & outcomes)")
        solara.DataFrame(agents_df, items_per_page=10)
    else:
        solara.Markdown("No agent data.")


@solara.component
def ConfigPanel():
    solara.Markdown("### Configuration")

    # Scenario Selector
    if manager.scenarios.value:
        solara.Select(
            label="Load Scenario",
            values=list(manager.scenarios.value.keys()),
            value=manager.selected_scenario,
            on_value=manager.apply_scenario,
        )
        solara.Markdown("---")

    # Live Config controls (Always enabled now)
    # Removing 'disabled' logic and Restore buttons.

    with solara.lab.Tabs():
        with solara.lab.Tab("General"):
            solara.Markdown("**Simulation Parameters**")
            solara.InputInt(label="Steps", value=manager.steps)
            solara.InputInt(label="N Agents", value=manager.n_agents)
            solara.InputInt(label="Token Cap (Q)", value=manager.token_cap)

        with solara.lab.Tab("Audit"):
            solara.Markdown("**Governor (Audit) Policy**")
            solara.InputFloat(label="Penalty (P)", value=manager.penalty)
            solara.InputFloat(label="Base Prob (pi_0)", value=manager.base_prob)
            solara.InputFloat(label="High Prob (pi_1)", value=manager.high_prob)
            solara.InputFloat(label="Signal TPR", value=manager.signal_tpr)
            solara.InputFloat(label="Signal FPR", value=manager.signal_fpr)
            solara.InputInt(
                label="Audit Budget (Count)",
                value=manager.audit_budget,
            )

        with solara.lab.Tab("Lab"):
            solara.Markdown("**Lab Agent Generation**")
            solara.Markdown("*Gross Value Range*")
            solara.InputFloat(label="Min", value=manager.gross_value_min)
            solara.InputFloat(label="Max", value=manager.gross_value_max)
            solara.Markdown("*Risk Profile Range*")
            solara.InputFloat(label="Min", value=manager.risk_profile_min)
            solara.InputFloat(label="Max", value=manager.risk_profile_max)

    solara.Markdown("---")
    with solara.Row():
        solara.Button("Reset", on_click=manager.reset_model, color="error")
        # Hiding Step button for batch-mode feel, or keep it?
        # User said "when run is done... auto load".
        # Keeping manual Step is useful for debugging, but maybe de-emphasize?
        # Leaving it for now as "Advanced".
        solara.Button(
            "Step",
            on_click=manager.step,
            disabled=manager.is_playing.value,
        )

    solara.Button(
        label="Pause" if manager.is_playing.value else "Play",
        on_click=lambda: manager.is_playing.set(not manager.is_playing.value),
        color="primary",
    )


@solara.component
def EmptyState():
    with solara.Column(
        style="height: 60vh; justify-content: center; align-items: center; color: #888;"
    ):
        # Using a large icon and clear CTA
        solara.Markdown("## Ready to Simulate")
        solara.Markdown("Configure parameters on the left and click **Play**.")


@solara.component
def LoadingState():
    with solara.Column(
        style="height: 60vh; justify-content: center; align-items: center;"
    ):
        solara.v.ProgressCircular(indeterminate=True, color="primary", size=50)
        solara.Text("Simulating Scenario...", classes=["mt-4", "text-xl", "font-bold"])


@solara.component
def Page():
    # Initialize if needed
    if manager.model.value is None:
        manager.reset_model()

    # Mount the controller (handles the loop)
    SimulationController()

    with solara.Sidebar():
        ConfigPanel()
        solara.Markdown("---")
        # RunHistoryList moved to main page

    solara.Title("Compute Permit Market Simulator")

    # --- Right Pane State Machine ---
    has_data = (manager.step_count.value > 0) or (
        manager.selected_run.value is not None
    )
    is_playing = manager.is_playing.value

    if is_playing:
        LoadingState()
    elif not has_data:
        EmptyState()
    else:
        with solara.lab.Tabs():
            with solara.lab.Tab("Dashboard"):
                Dashboard()
            with solara.lab.Tab("Inspector"):
                InspectorTab()

    # Run History at the bottom
    solara.Markdown("---")
    with solara.v.ExpansionPanels():
        with solara.v.ExpansionPanel():
            with solara.v.ExpansionPanelHeader():
                solara.Text("Previous Runs")
            with solara.v.ExpansionPanelContent():
                RunHistoryList()
