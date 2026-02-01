from compute_permit_sim.domain.market import SimpleClearingMarket


def test_market_clearing_scarce():
    """Test clearing price when demand > supply.

    Ref: technical_specification.md Section 2.3 "Clearing Market"
    """
    market = SimpleClearingMarket(token_cap=2)
    bids = [(1, 10.0), (2, 9.0), (3, 8.0), (4, 7.0)]

    # Clearing price is set by the Nth highest bid (marginal bid).
    # With cap=2, the 2nd highest bid (9.0) sets the price.
    price, winners = market.allocate(bids)
    assert price == 9.0
    assert set(winners) == {1, 2}


def test_market_clearing_surplus():
    """Test clearing price when supply > demand.

    Ref: technical_specification.md Section 2.3 "Clearing Market"
    """
    market = SimpleClearingMarket(token_cap=10)
    bids = [(1, 10.0), (2, 9.0)]
    price, winners = market.allocate(bids)
    assert price == 0.0
    assert set(winners) == {1, 2}


def test_fixed_price_market():
    """Test market behavior with fixed price (unlimited supply).

    Ref: technical_specification.md Section 2.3 "Fixed Price Market"
    """
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
    """Test fixed price market with no bids."""
    market = SimpleClearingMarket(token_cap=100)
    market.set_fixed_price(5.0)

    # If no bids, price defaults to 0.0 (no transactions occurred)
    price, winners = market.allocate([])
    assert price == 0.0
    assert winners == []
