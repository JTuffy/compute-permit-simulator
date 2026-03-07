"""Unit tests for vis.transforms — pure data-prep functions.

No matplotlib or Solara dependencies; tests work purely on DataFrames.
"""

import pandas as pd
import pytest

from compute_permit_sim.schemas.columns import ColumnNames
from compute_permit_sim.vis.transforms import (
    classify_agent_outcome,
    compute_net_payoff,
)

# ---------------------------------------------------------------------------
# classify_agent_outcome
# ---------------------------------------------------------------------------


def _make_agents_df(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal agents DataFrame from dicts."""
    defaults: dict = {
        ColumnNames.IS_COMPLIANT: True,
        ColumnNames.WAS_CAUGHT: False,
        ColumnNames.ECONOMIC_VALUE: 10.0,
        ColumnNames.BID_PRICE: 2.0,
        ColumnNames.PERMITS_WANTED: 1,
        ColumnNames.PENALTY_AMOUNT: 0.0,
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


def test_classify_agent_outcome_compliant():
    df = _make_agents_df(
        [{ColumnNames.IS_COMPLIANT: True, ColumnNames.WAS_CAUGHT: False}]
    )
    result = classify_agent_outcome(df)
    assert result["outcome"].iloc[0] == "Compliant"


def test_classify_agent_outcome_caught():
    df = _make_agents_df(
        [{ColumnNames.IS_COMPLIANT: False, ColumnNames.WAS_CAUGHT: True}]
    )
    result = classify_agent_outcome(df)
    assert result["outcome"].iloc[0] == "Caught"


def test_classify_agent_outcome_uncaught():
    df = _make_agents_df(
        [{ColumnNames.IS_COMPLIANT: False, ColumnNames.WAS_CAUGHT: False}]
    )
    result = classify_agent_outcome(df)
    assert result["outcome"].iloc[0] == "Uncaught"


def test_classify_agent_outcome_all_three():
    df = _make_agents_df(
        [
            {ColumnNames.IS_COMPLIANT: True, ColumnNames.WAS_CAUGHT: False},
            {ColumnNames.IS_COMPLIANT: False, ColumnNames.WAS_CAUGHT: True},
            {ColumnNames.IS_COMPLIANT: False, ColumnNames.WAS_CAUGHT: False},
        ]
    )
    result = classify_agent_outcome(df)
    assert set(result["outcome"].tolist()) == {"Compliant", "Caught", "Uncaught"}


def test_classify_agent_outcome_missing_columns():
    """Graceful fallback when required columns are absent."""
    df = pd.DataFrame([{"some_other_col": 1}])
    result = classify_agent_outcome(df)
    assert "outcome" in result.columns
    assert result["outcome"].iloc[0] == "Unknown"


# ---------------------------------------------------------------------------
# compute_net_payoff
# ---------------------------------------------------------------------------


def test_compute_net_payoff_formula():
    """net_payoff = economic_value - bid_price*permits_wanted - penalty_amount."""
    df = _make_agents_df(
        [
            {
                ColumnNames.ECONOMIC_VALUE: 10.0,
                ColumnNames.BID_PRICE: 2.0,
                ColumnNames.PERMITS_WANTED: 3,
                ColumnNames.PENALTY_AMOUNT: 1.0,
            }
        ]
    )
    result = compute_net_payoff(df)
    # 10 - 2*3 - 1 = 3
    assert result[ColumnNames.NET_PAYOFF].iloc[0] == pytest.approx(3.0)


def test_compute_net_payoff_no_deductions():
    df = _make_agents_df(
        [
            {
                ColumnNames.ECONOMIC_VALUE: 5.0,
                ColumnNames.BID_PRICE: 0.0,
                ColumnNames.PERMITS_WANTED: 0,
                ColumnNames.PENALTY_AMOUNT: 0.0,
            }
        ]
    )
    result = compute_net_payoff(df)
    assert result[ColumnNames.NET_PAYOFF].iloc[0] == pytest.approx(5.0)


def test_compute_net_payoff_missing_columns():
    """Gracefully adds zero net_payoff when required columns are absent."""
    df = pd.DataFrame([{"some_col": 1}])
    result = compute_net_payoff(df)
    assert ColumnNames.NET_PAYOFF in result.columns
    assert result[ColumnNames.NET_PAYOFF].iloc[0] == 0.0


# ---------------------------------------------------------------------------
