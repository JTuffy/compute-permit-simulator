"""Data collection logic for the simulation."""

import mesa


def compute_compliance_rate(model: mesa.Model) -> float:
    """Calculate the percentage of labs that are compliant.

    Args:
        model: The Mesa model instance.

    Returns:
        float: Compliance rate (0.0 to 1.0).
    """
    agents = [a for a in model.agents if hasattr(a, "domain_agent")]
    if not agents:
        return 0.0
    compliant_count = sum(1 for a in agents if a.domain_agent.is_compliant)
    return compliant_count / len(agents)


def compute_average_price(model: mesa.Model) -> float:
    """Get the current market price.

    Args:
        model: The Mesa model instance.

    Returns:
        float: Current price.
    """
    if hasattr(model, "market"):
        return model.market.current_price
    return 0.0
