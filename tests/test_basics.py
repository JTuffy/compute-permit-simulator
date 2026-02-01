from compute_permit_sim.domain.agents import Lab
from compute_permit_sim.domain.enforcement import Auditor
from compute_permit_sim.domain.market import SimpleClearingMarket
from compute_permit_sim.schemas import AuditConfig


def test_lab_initialization():
    lab = Lab(lab_id=1, gross_value=1.5)
    assert lab.lab_id == 1
    assert lab.gross_value == 1.5
    assert lab.is_compliant is True
    assert lab.has_permit is False
    assert lab.get_bid() == 1.5


def test_auditor_initialization():
    config = AuditConfig(
        base_prob=0.1,
        high_prob=0.5,
        false_positive_rate=0.05,
        false_negative_rate=0.1,
        penalty_amount=0.8,
        backcheck_prob=0.2,
    )
    gov = Auditor(config)
    # Check effective detection (basic test)
    # beta = 0.9, p_s = 0.9*0.5 + 0.1*0.1 = 0.45 + 0.01 = 0.46
    # p_eff = 0.46 + (0.54)*0.2 = 0.46 + 0.108 = 0.568
    p_eff = gov.compute_effective_detection()
    assert abs(p_eff - 0.568) < 1e-6


def test_market_initialization():
    market = SimpleClearingMarket(token_cap=10)
    assert market.max_supply == 10
    assert market.current_price == 0.0
    assert market.fixed_price is None
