"""Market logic for compute permits."""

from typing import Protocol


class MarketMechanism(Protocol):
    """Protocol for a market mechanism."""

    def clear_market(self, demands: list[float], supplies: list[float]) -> float:
        """Calculate the clearing price based on demands and supplies.

        Args:
            demands: List of quantities demanded by agents (at 0 price, effectively).
            supplies: List of quantities supplied (e.g. total cap).

        Returns:
            The market clearing price.
        """
        ...


class SimpleClearingMarket:
    """A simple market that clears based on a demand-supply curve equivalent.

    For the MVP, we assume a simple linear inverse demand curve or similar mechanism
    if we don't have full Bid/Ask orders.
    However, the tech spec implies endogenous pricing: p = v* - c.
    In a perfect market, price equals marginal value of the marginal user.
    """

    def __init__(self, token_cap: float) -> None:
        """Initialize the market.

        Args:
            token_cap: The total number of permits available (Q).
        """
        self.max_supply: float = token_cap
        self.current_price: float = 0.0

    def resolve_price(self, bids: list[float]) -> float:
        """Resolve the market price based on agent valuations (bids).

        If demand > supply, the price is set by the valuation of the
        marginal winner (the lowest valuation that still gets in).
        Or strictly, the highest valuation that *doesn't* get in (Vickrey-ish),
        depending on the auction style. We'll use the marginal clearing price:
        The N-th highest bid, where N = supply.

        Args:
            bids: List of valuations (willingness to pay) from all agents.

        Returns:
            The clearing price.
        """
        # Sort bids descending
        sorted_bids = sorted(bids, reverse=True)
        available_permits = int(self.max_supply)

        if available_permits >= len(sorted_bids):
            # Surplus supply -> Price falls to 0 (or reserve)
            return 0.0

        # The price is determined by the marginal agent who just makes the cut,
        # or the one who just misses it.
        # Standard: Price is the valuation of the agent who *just misses* out?
        # Or the last one to get in?
        # Let's set it to the lowest winning bid to clear the market.
        clearing_price = sorted_bids[available_permits - 1]
        self.current_price = clearing_price
        return clearing_price
