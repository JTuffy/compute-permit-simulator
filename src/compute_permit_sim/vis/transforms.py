"""Pure data transform functions for the visualization layer.

This module is the boundary between raw simulation data (StepResult, AgentSnapshot)
and the chart rendering layer. All functions here:
  - Accept domain objects or DataFrames
  - Return DataFrames or dicts
  - Have zero matplotlib / Solara dependencies
  - Are independently unit-testable

Usage pattern::

    from compute_permit_sim.vis.transforms import classify_agent_outcome, compute_net_payoff

    df = classify_agent_outcome(agents_df)
    df = compute_net_payoff(df)
    fig = plot_payoff_comparison(df)   # in plotting.py
"""

from __future__ import annotations

import pandas as pd

from compute_permit_sim.schemas.columns import ColumnNames

# ---------------------------------------------------------------------------
# Single-step (agents_df) transforms
# ---------------------------------------------------------------------------


def classify_agent_outcome(agents_df: pd.DataFrame) -> pd.DataFrame:
    """Add an ``outcome`` column classifying each agent as Compliant / Caught / Uncaught.

    The three categories are mutually exclusive and exhaustive:
      - ``"Caught"``    — was audited and caught (non-compliant + caught)
      - ``"Uncaught"``  — non-compliant but not caught
      - ``"Compliant"`` — compliant this step

    Args:
        agents_df: Step-level agent DataFrame with at minimum
            ``is_compliant`` and ``was_caught`` columns.

    Returns:
        Copy of *agents_df* with a new ``outcome`` string column.
    """
    df = agents_df.copy()
    if (
        ColumnNames.IS_COMPLIANT not in df.columns
        or ColumnNames.WAS_CAUGHT not in df.columns
    ):
        df["outcome"] = "Unknown"
        return df

    def _label(row: pd.Series) -> str:
        if row[ColumnNames.WAS_CAUGHT]:
            return "Caught"
        if not row[ColumnNames.IS_COMPLIANT]:
            return "Uncaught"
        return "Compliant"

    df["outcome"] = df.apply(_label, axis=1)
    return df


def compute_net_payoff(agents_df: pd.DataFrame) -> pd.DataFrame:
    """Add a ``net_payoff`` column representing realised economic outcome per lab.

    Formula:
        net_payoff = economic_value
                     - (bid_price × permits_wanted)
                     - penalty_amount

    This is the *actual* profit from the step: gross value minus permit cost
    minus any penalty assessed.

    Args:
        agents_df: Step-level agent DataFrame.

    Returns:
        Copy of *agents_df* with a new ``net_payoff`` float column.
    """
    df = agents_df.copy()
    required = [
        ColumnNames.ECONOMIC_VALUE,
        ColumnNames.BID_PRICE,
        ColumnNames.PERMITS_WANTED,
        ColumnNames.PENALTY_AMOUNT,
    ]
    if not all(c in df.columns for c in required):
        df[ColumnNames.NET_PAYOFF] = 0.0
        return df

    df[ColumnNames.NET_PAYOFF] = (
        df[ColumnNames.ECONOMIC_VALUE]
        - df[ColumnNames.BID_PRICE] * df[ColumnNames.PERMITS_WANTED]
        - df[ColumnNames.PENALTY_AMOUNT]
    )
    return df


# ---------------------------------------------------------------------------
# Run-level (list[StepResult]) transforms
# ---------------------------------------------------------------------------


def compute_compliance_series(steps: list) -> list[tuple[int, float]]:
    """Compute aggregate compliance rate at each step.

    Args:
        steps: List of ``StepResult`` objects ordered by step number.

    Returns:
        List of ``(step_number, compliance_rate)`` tuples.
    """
    from compute_permit_sim.services.metrics import calculate_compliance

    return [(s.step, calculate_compliance(s.agents)) for s in steps]


def compute_price_series(steps: list) -> list[tuple[int, float]]:
    """Extract clearing price at each step.

    Args:
        steps: List of ``StepResult`` objects.

    Returns:
        List of ``(step_number, price)`` tuples.
    """
    return [(s.step, s.market.price) for s in steps]


def compute_audit_source_counts(steps: list) -> pd.DataFrame:
    """Count caught events by AuditSource across all steps.

    Args:
        steps: List of ``StepResult`` objects.

    Returns:
        DataFrame with columns: ``source``, ``count``.
        Only sources with count > 0 are included.
    """
    counts: dict[str, int] = {}
    for s in steps:
        for agent in s.agents:
            source = getattr(agent, ColumnNames.CAUGHT_SOURCE, None)
            if source is not None:
                # Accept both enum and string representations
                label = source.value if hasattr(source, "value") else str(source)
                counts[label] = counts.get(label, 0) + 1
    if not counts:
        return pd.DataFrame(columns=["source", "count"])
    return pd.DataFrame([{"source": k, "count": v} for k, v in sorted(counts.items())])


# ---------------------------------------------------------------------------
# Simulation-wide aggregate transforms (consolidate over all steps)
# ---------------------------------------------------------------------------


def aggregate_risk_scatter(steps: list) -> pd.DataFrame:
    """Aggregate all per-step agent observations into one scatter-ready DataFrame.

    Concatenates agent snapshots from every step so the sim-wide scatter plot
    shows each lab's position across the full run rather than a single step.
    Complies with the same column contract as the step-wise scatter.

    Args:
        steps: List of StepResult objects.

    Returns:
        DataFrame with one row per (step, agent) with columns:
        reported_training_flops, used_training_flops, is_compliant, step.
    """
    all_rows = []
    for s in steps:
        for a in s.agents:
            all_rows.append(
                {
                    ColumnNames.REPORTED_TRAINING_FLOPS: a.reported_training_flops,
                    ColumnNames.USED_TRAINING_FLOPS: a.used_training_flops,
                    ColumnNames.IS_COMPLIANT: a.is_compliant,
                    "step": s.step,
                }
            )
    if not all_rows:
        return pd.DataFrame()
    return pd.DataFrame(all_rows)


def aggregate_audit_targeting(steps: list) -> dict:
    """Aggregate audit targeting statistics across all steps.

    Returns the overall fraction of compliant and non-compliant labs
    that were audited across the full run.

    Args:
        steps: List of StepResult objects.

    Returns:
        Dict with keys:
          compliant_audits, compliant_total,
          noncompliant_audits, noncompliant_total,
          compliant_rate, noncompliant_rate.
    """
    ca = ct = na = nt = 0
    for s in steps:
        for a in s.agents:
            audited = getattr(a, "was_audited", False)
            compliant = getattr(a, "is_compliant", True)
            if compliant:
                ct += 1
                if audited:
                    ca += 1
            else:
                nt += 1
                if audited:
                    na += 1

    return {
        "compliant_audits": ca,
        "compliant_total": ct,
        "noncompliant_audits": na,
        "noncompliant_total": nt,
        "compliant_rate": ca / ct if ct > 0 else 0.0,
        "noncompliant_rate": na / nt if nt > 0 else 0.0,
    }


def aggregate_compliance_distribution(steps: list) -> pd.DataFrame:
    """Aggregate outcome + audit source across all steps into one DataFrame.

    Effectively concatenates agent outcomes from every step so the sim-wide
    compliance distribution plot can show catch totals and their source channels.

    Args:
        steps: List of StepResult objects.

    Returns:
        Long-form DataFrame with columns: outcome, caught_source (may be None).
    """
    rows = []
    for s in steps:
        agent_rows = [a.model_dump() for a in s.agents]
        if not agent_rows:
            continue
        step_df = pd.DataFrame(agent_rows)
        step_df = classify_agent_outcome(step_df)
        for _, row in step_df.iterrows():
            rows.append(
                {
                    "outcome": row["outcome"],
                    "caught_source": row.get(ColumnNames.CAUGHT_SOURCE)
                    if row["outcome"] == "Caught"
                    else None,
                }
            )
    if not rows:
        return pd.DataFrame(columns=["outcome", "caught_source"])
    return pd.DataFrame(rows)
