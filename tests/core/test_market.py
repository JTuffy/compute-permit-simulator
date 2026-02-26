"""Tests for Market mechanism and clearing."""

from compute_permit_sim.core.market import SimpleClearingMarket


def test_market_initialization() -> None:
    """Verify that the SimpleClearingMarket initializes with correct supply and default price."""
    market = SimpleClearingMarket(permit_cap=10)
    assert market.max_supply == 10
    assert market.current_price == 0.0
    assert market.fixed_price is None


def test_market_clearing_scarce():
    """Test clearing price when demand > supply (binary: quantity=1)."""
    market = SimpleClearingMarket(permit_cap=2)
    bids = [(1, 1, 10.0), (2, 1, 9.0), (3, 1, 8.0), (4, 1, 7.0)]

    price, allocations = market.allocate(bids)
    assert price == 9.0
    assert allocations[1] == 1
    assert allocations[2] == 1
    assert allocations[3] == 0
    assert allocations[4] == 0


def test_market_clearing_surplus():
    """Test clearing price when supply > demand (binary: quantity=1)."""
    market = SimpleClearingMarket(permit_cap=10)
    bids = [(1, 1, 10.0), (2, 1, 9.0)]
    price, allocations = market.allocate(bids)
    assert price == 0.0
    assert allocations[1] == 1
    assert allocations[2] == 1


def test_fixed_price_market():
    """Test fixed-price market: qualifying labs get permits when supply is sufficient."""
    market = SimpleClearingMarket(permit_cap=10)  # Enough for all qualifying labs
    market.set_fixed_price(5.0)

    bids = [(1, 1, 10.0), (2, 1, 5.0), (3, 1, 4.9), (4, 1, 1.0)]

    price, allocations = market.allocate(bids)

    assert price == 5.0
    assert allocations[1] == 1  # bid >= fixed_price
    assert allocations[2] == 1  # bid == fixed_price
    assert allocations[3] == 0  # bid < fixed_price
    assert allocations[4] == 0  # bid < fixed_price


def test_fixed_price_market_oversubscribed():
    """Test fixed-price market when demand exceeds permit_cap: random allocation."""
    market = SimpleClearingMarket(permit_cap=1)  # Only 1 permit for 2 qualifying labs
    market.set_fixed_price(5.0)

    bids = [(1, 1, 10.0), (2, 1, 5.0), (3, 1, 4.9)]

    price, allocations = market.allocate(bids)

    assert price == 5.0
    # Exactly 1 permit allocated total across qualifying labs (1 and 2)
    assert allocations[3] == 0
    assert allocations[1] + allocations[2] == 1


def test_fixed_price_no_bids():
    """Test fixed price market with no bids."""
    market = SimpleClearingMarket(permit_cap=100)
    market.set_fixed_price(5.0)

    price, allocations = market.allocate([])
    assert price == 0.0
    assert allocations == {}


def test_multi_unit_allocation():
    """Test multi-unit auction: firms bid for different quantities.

    Supply = 5 permits.
    Firm 1: wants 3 permits at 10.0 each → 3 units
    Firm 2: wants 2 permits at 8.0 each → 2 units
    Firm 3: wants 2 permits at 6.0 each → 2 units (only 0 allocated)
    Total demand = 7 > supply = 5.
    Sorted units: [1@10, 1@10, 1@10, 2@8, 2@8, 3@6, 3@6]
    Top 5: firm1 gets 3, firm2 gets 2. Clearing price = 8.0.
    """
    market = SimpleClearingMarket(permit_cap=5)
    bids = [(1, 3, 10.0), (2, 2, 8.0), (3, 2, 6.0)]

    price, allocations = market.allocate(bids)
    assert price == 8.0
    assert allocations[1] == 3
    assert allocations[2] == 2
    assert allocations[3] == 0


def test_multi_unit_surplus():
    """Test multi-unit with surplus supply — everyone gets what they want."""
    market = SimpleClearingMarket(permit_cap=20)
    bids = [(1, 3, 10.0), (2, 2, 5.0)]

    price, allocations = market.allocate(bids)
    assert price == 0.0
    assert allocations[1] == 3
    assert allocations[2] == 2


def test_multi_unit_fixed_price():
    """Test multi-unit with fixed price — firms get full demand if willing to pay."""
    market = SimpleClearingMarket(permit_cap=10)
    market.set_fixed_price(7.0)

    bids = [(1, 3, 10.0), (2, 2, 7.0), (3, 4, 5.0)]

    price, allocations = market.allocate(bids)
    assert price == 7.0
    assert allocations[1] == 3
    assert allocations[2] == 2
    assert allocations[3] == 0


def test_multi_unit_partial_allocation():
    """Test that a firm can receive fewer permits than demanded.

    Supply = 4. Firm 1 wants 3 at 10, Firm 2 wants 3 at 8.
    Units: [1@10, 1@10, 1@10, 2@8, 2@8, 2@8]
    Top 4: firm1 gets 3, firm2 gets 1. Clearing price = 8.0.
    """
    market = SimpleClearingMarket(permit_cap=4)
    bids = [(1, 3, 10.0), (2, 3, 8.0)]

    price, allocations = market.allocate(bids)
    assert price == 8.0
    assert allocations[1] == 3
    assert allocations[2] == 1
