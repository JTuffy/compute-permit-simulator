from compute_permit_sim.domain.market import SimpleClearingMarket


def test_market_clearing_scarce():
    """Test clearing price when demand > supply."""
    market = SimpleClearingMarket(token_cap=2)
    bids = [(1, 10.0), (2, 9.0), (3, 8.0), (4, 7.0)]
    # Top 2 bids are 10.0 and 9.0.
    # Clearing price should be the 2nd highest bid (marginal bid) -> 9.0?
    # Wait, simple marginal pricing usually means the Nth highest bid sets the price.
    # Code says: clearing_price = sorted_bids[available_permits - 1]
    # So index 2-1=1 -> 2nd item -> 9.0.
    price, winners = market.allocate(bids)
    assert price == 9.0
    assert set(winners) == {1, 2}


def test_market_clearing_surplus():
    """Test clearing price when supply > demand."""
    market = SimpleClearingMarket(token_cap=10)
    bids = [(1, 10.0), (2, 9.0)]
    price, winners = market.allocate(bids)
    assert price == 0.0
    assert set(winners) == {1, 2}


def test_fixed_price_market():
    """Test market behavior with fixed price (unlimited supply)."""
    market = SimpleClearingMarket(token_cap=0)  # Cap shouldn't matter
    market.set_fixed_price(5.0)

    # Bids: some above, some below
    bids = [(1, 10.0), (2, 5.0), (3, 4.9), (4, 1.0)]

    price, winners = market.allocate(bids)

    assert price == 5.0
    assert set(winners) == {1, 2}  # 1 and 2 bid >= 5.0
    assert 3 not in winners
    assert 4 not in winners


def test_fixed_price_no_bids():
    market = SimpleClearingMarket(token_cap=100)
    market.set_fixed_price(5.0)
    price, winners = market.allocate([])
    assert price == 0.0  # Or should it be fixed price?
    # Current implementation resets to 0.0 if no bids.
    # But usually fixed price persists.
    # Let's check implementation behavior:
    # "if not bids: self.current_price = 0.0; return 0.0, []"
    # This might be a slight inconsistency if we want rigid fixed price,
    # but functionally it acts as "no transactions".
    assert winners == []
