
import pytest
from cpm_simulator.model import ComputePermitMarketModel

def test_model_initialization():
    model = ComputePermitMarketModel(N=10)
    assert model.num_agents == 10
    assert len(model.agents) == 10

def test_compliance_logic():
    # Case 1: p * B > g (Should Comply)
    # p=0.5, B=100 => 50. g = 100 * 0.1 (price 0.1) = 10. 50 > 10.
    
    # We need to control the market price or firm capacity to test this.
    model = ComputePermitMarketModel(N=1, detection_probability=0.5, penalty=100.0)
    agent = model.agents[0]
    
    # Force market price to be low enough that complying is better
    model.market.current_price = 0.1 
    # Firm capacity 100. g = 10. p*B = 50. 
    # 50 >= 10 -> Compliant
    
    agent.step()
    assert agent.is_compliant == True

def test_non_compliance_logic():
    # Case 2: p * B < g (Should Cheat)
    # p=0.1, B=10. => 1. 
    # Price = 0.1. Capacity 100. g = 10.
    # 1 < 10 -> Non-compliant
    
    model = ComputePermitMarketModel(N=1, detection_probability=0.1, penalty=10.0)
    model.market.current_price = 0.1
    agent = model.agents[0]
    
    agent.step()
    assert agent.is_compliant == False
