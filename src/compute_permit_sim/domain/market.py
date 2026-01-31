"""Market logic for compute permits.

Implements a simple marginal-bid clearing mechanism.
Tech spec section 4: "(1) Market Price Discovery -> (2) Permit Allocation"
should be logically paired in the market module.
"""

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
    """A simple market that clears based on marginal-bid pricing.

    The Qth highest bid sets the clearing price. All bidders at or above
    the clearing price receive a permit. When supply exceeds demand,
    the price falls to 0.

    Attributes:
        max_supply: Total permits available (Q).
        current_price: The most recent clearing price.
    """

    def __init__(self, token_cap: float) -> None:
        """Initialize the market.

        Args:
            token_cap: The total number of permits available (Q).
        """
        self.max_supply: float = token_cap
        self.current_price: float = 0.0
        self.fixed_price: float | None = None

    def set_fixed_price(self, price: float) -> None:
        """Set a fixed price for the market (unlimited supply mode)."""
        self.fixed_price = price

    def resolve_price(self, bids: list[float]) -> float:
        """Resolve the market price based on agent valuations (bids).

        The clearing price is the Qth highest bid (lowest winning bid).
        If supply >= demand, the price is 0.

        Args:
            bids: List of valuations (willingness to pay) from all agents.

        Returns:
            The clearing price.
        """
        if not bids:
            self.current_price = 0.0
            return 0.0

        sorted_bids = sorted(bids, reverse=True)
        available_permits = int(self.max_supply)

        if available_permits >= len(sorted_bids):
            self.current_price = 0.0
            return 0.0

        clearing_price = sorted_bids[available_permits - 1]
        self.current_price = clearing_price
        return clearing_price

    def allocate(self, bids: list[tuple[int, float]]) -> tuple[float, list[int]]:
        """Resolve price and allocate permits to the highest bidders.

        Combines price discovery and allocation into a single call
        (tech spec section 4 turn sequence phases 1-2).

        Args:
            bids: List of (lab_id, bid_value) pairs.

        Returns:
            Tuple of (clearing_price, list of winning lab_ids).
            Winners are the top Q bidders whose bid >= clearing price.
        """
        if not bids:
            self.current_price = 0.0
            return 0.0, []

        # FIXED PRICE MODE
        if self.fixed_price is not None:
            self.current_price = self.fixed_price
            # Everyone willing to pay the fixed price gets a permit (unlimited supply)
            winners = [
                lab_id for lab_id, bid_value in bids if bid_value >= self.fixed_price
            ]
            return self.fixed_price, winners

        available_permits = int(self.max_supply)

        # Sort by bid value descending, then by lab_id ascending for deterministic ties
        sorted_bids = sorted(bids, key=lambda x: (-x[1], x[0]))

        if available_permits >= len(sorted_bids):
            # Surplus supply: everyone gets a permit, price = 0
            self.current_price = 0.0
            return 0.0, [lab_id for lab_id, _ in sorted_bids]

        # Clearing price = Qth highest bid (lowest winning bid)
        clearing_price = sorted_bids[available_permits - 1][1]
        self.current_price = clearing_price

        # Winners: top Q bidders whose bid >= clearing price
        winners = [
            lab_id
            for lab_id, bid_value in sorted_bids[:available_permits]
            if bid_value >= clearing_price
        ]

        return clearing_price, winners
