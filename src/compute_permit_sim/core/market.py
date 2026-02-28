"""Market logic for compute permits.

Implements a simple marginal-bid clearing mechanism.
Tech spec section 4: "(1) Market Price Discovery -> (2) Permit Allocation"
should be logically paired in the market module.
"""

import random
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

    def __init__(self, permit_cap: float, fixed_price: float | None = None) -> None:
        """Initialize the market.

        Args:
            permit_cap: The total number of permits available (Q).
        """
        self.max_supply: float = permit_cap
        self.current_price: float = 0.0
        self.fixed_price: float | None = None

    def set_fixed_price(self, price: float) -> None:
        """Set a fixed price for the market.

        All labs willing to pay at least this price qualify for permits.
        If qualifying demand exceeds permit_cap, permits are randomly allocated.

        Args:
            price: The fixed price for permits.
        """
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

    def allocate(
        self, bids: list[tuple[int, int, float]]
    ) -> tuple[float, dict[int, int]]:
        """Resolve price and allocate permits via uniform-price auction.

        Supports both binary (quantity=1) and multi-unit (FLOP-denominated)
        permits through the same mechanism:

        1. Each firm submits (lab_id, quantity_demanded, bid_per_permit).
           For binary permits, every firm submits quantity=1.
        2. Bids are expanded into individual permit-units, each tagged with
           the firm's per-permit bid.
        3. Units are sorted by bid descending (ties broken by lab_id asc).
        4. The top ``permit_cap`` units are allocated.
        5. The clearing price is the bid of the marginal (last allocated) unit.
           All winners pay this uniform price per permit.

        Fixed-price mode: if ``fixed_price`` is set, qualifying firms (bid >=
        fixed_price) receive permits at that price. If total qualifying units
        exceed ``permit_cap``, permits are randomly allocated up to the cap.

        Args:
            bids: List of (lab_id, quantity_demanded, bid_per_permit).
                ``quantity_demanded``: how many permits the firm wants (>=0).
                ``bid_per_permit``: willingness to pay per single permit.

        Returns:
            Tuple of (clearing_price, allocations):
                ``clearing_price``: uniform price per permit.
                ``allocations``: {lab_id: number_of_permits_allocated}.
        """
        allocations: dict[int, int] = {lab_id: 0 for lab_id, _, _ in bids}

        if not bids:
            self.current_price = 0.0
            return 0.0, allocations

        # FIXED PRICE MODE — all qualifying bidders pay fixed_price
        # If total qualifying units <= permit_cap: all get their requested permits.
        # If total qualifying units > permit_cap: randomly allocate up to cap.
        if self.fixed_price is not None:
            self.current_price = self.fixed_price
            qualifying: list[tuple[int, int]] = [
                (lab_id, qty)
                for lab_id, qty, bid_per in bids
                if bid_per >= self.fixed_price
            ]
            # Expand to individual permit-units tagged with lab_id
            fp_units: list[int] = []
            for lab_id, qty in qualifying:
                fp_units.extend(lab_id for _ in range(qty))

            available = int(self.max_supply)
            if len(fp_units) <= available:
                # Enough supply: every qualifying lab gets what they asked for
                for lab_id, qty in qualifying:
                    allocations[lab_id] = qty
            else:
                # Over-subscribed: randomly sample up to permit_cap units
                winners = random.sample(fp_units, available)
                for lab_id in winners:
                    allocations[lab_id] += 1

            return self.fixed_price, allocations

        # AUCTION MODE — expand bids to individual permit-units
        units: list[tuple[int, float]] = []
        for lab_id, qty, bid_per in bids:
            units.extend((lab_id, bid_per) for _ in range(qty))

        if not units:
            self.current_price = 0.0
            return 0.0, allocations

        # Sort: highest bid first, then lowest lab_id for deterministic ties
        units.sort(key=lambda x: (-x[1], x[0]))

        available = int(self.max_supply)

        if available >= len(units):
            # Surplus supply: everyone gets what they asked for, price = 0
            self.current_price = 0.0
            for lab_id, qty, _ in bids:
                allocations[lab_id] = qty
            return 0.0, allocations

        # Clearing price = bid of the Qth highest unit (marginal winner)
        clearing_price = units[available - 1][1]
        self.current_price = clearing_price

        # Allocate the top `available` units whose bid >= clearing price
        for lab_id, bid_per in units[:available]:
            if bid_per >= clearing_price:
                allocations[lab_id] += 1

        return clearing_price, allocations
