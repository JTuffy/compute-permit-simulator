"""Data collection logic for the simulation."""

import mesa


def compute_compliance_rate(model: mesa.Model) -> float:
    """Calculate the percentage of labs that are compliant.

    Args:
        model: The Mesa model instance.

    Returns:
        float: Compliance rate (0.0 to 1.0).
    """
    from compute_permit_sim.services.model_wrapper import MesaLab

    if not model.agents:
        return 0.0

    # Filter strictly for MesaLab instances
    agents = [a for a in model.agents if isinstance(a, MesaLab)]
    if not agents:
        return 0.0

    compliant_count = sum(1 for a in agents if a.domain_agent.is_compliant)
    return compliant_count / len(agents)


def compute_current_price(model: mesa.Model) -> float:
    """Get the current market price.

    Args:
        model: The Mesa model instance.

    Returns:
        float: Current price.
    """
    from compute_permit_sim.services.model_wrapper import ComputePermitModel

    if isinstance(model, ComputePermitModel):
        return model.market.current_price
    return 0.0
