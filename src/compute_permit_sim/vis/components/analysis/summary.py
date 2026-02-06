import solara

from compute_permit_sim.vis.components import MetricCard
from compute_permit_sim.vis.state.active import active_sim


@solara.component
def AnalysisSummary(
    is_live: bool,
    config,
    step_count: int,
    compliance_series: list,
    price_series: list,
):
    """Summary card showing key metrics and run configuration details."""
    # --- Compute derived values for cards ---
    current_compliance = "N/A"
    comp_color = "primary"
    if compliance_series:
        comp_val = compliance_series[-1]
        current_compliance = f"{comp_val:.1%}"
        comp_color = "success" if comp_val >= 0.8 else "warning"

    current_price = f"${price_series[-1]:.2f}" if price_series else "N/A"

    with solara.Card("Key Metrics"):
        # Determine seed to display
        display_seed = "Random"
        if is_live:
            if active_sim.state.value.actual_seed is not None:
                display_seed = str(active_sim.state.value.actual_seed)
        elif config and config.seed is not None:
            display_seed = str(config.seed)

        with solara.Columns([1, 1, 1, 1]):
            MetricCard("Steps", f"{step_count}", "primary")
            MetricCard("Compliance", current_compliance, comp_color)
            MetricCard("Price", current_price, "primary")
            MetricCard("Seed", display_seed, "secondary")

    # Run Configuration (Historical Only)
    if config is not None:
        with solara.Card():
            with solara.Details("Run Configuration", expand=False):
                c = config
                with solara.lab.Tabs():
                    with solara.lab.Tab("General"):
                        with solara.Columns([1, 1]):
                            with solara.Column():
                                solara.Markdown(f"**Steps:** {c.steps}")
                                solara.Markdown(f"**Agents:** {c.n_agents}")
                            with solara.Column():
                                solara.Markdown(
                                    f"**Token Cap:** {int(c.market.token_cap)}"
                                )

                    with solara.lab.Tab("Audit Policy"):
                        with solara.Columns([1, 1]):
                            with solara.Column():
                                solara.Markdown(f"**Base π₀:** {c.audit.base_prob:.2%}")
                                solara.Markdown(f"**High π₁:** {c.audit.high_prob:.2%}")
                                solara.Markdown(
                                    f"**Penalty:** ${c.audit.penalty_amount:.0f}"
                                )
                            with solara.Column():
                                solara.Markdown(
                                    f"**TPR:** {1 - c.audit.false_negative_rate:.2%}"
                                )
                                solara.Markdown(
                                    f"**FPR:** {c.audit.false_positive_rate:.2%}"
                                )

                    with solara.lab.Tab("Lab Dynamics"):
                        with solara.Columns([1, 1]):
                            with solara.Column():
                                solara.Markdown(
                                    f"**Racing cr:** {c.lab.racing_factor:.2f}"
                                )
                                solara.Markdown(
                                    f"**Capability Vb:** {c.lab.capability_value:.2f}"
                                )
                            with solara.Column():
                                solara.Markdown(
                                    f"**Reputation β:** {c.lab.reputation_sensitivity:.2f}"
                                )
                                solara.Markdown(
                                    f"**Audit Coeff:** {c.lab.audit_coefficient:.2f}"
                                )
