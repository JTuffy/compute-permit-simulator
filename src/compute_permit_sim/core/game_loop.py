"""Core game loop — pure business logic for one simulation step.

Orchestrates the six-phase turn sequence:
    0. Collateral posting (above-threshold labs only)
    1. Trading (bids + market allocation, above-threshold labs only)
    2. Compliance decisions (above-threshold labs with excess only)
    3–4. Signal generation, audits, enforcement (above-threshold labs only)
    5. Value realization (labs that ran earn economic_value)
    6. Dynamic factor updates (decay, racing)

All functions operate on domain objects (Lab, SimpleClearingMarket, Auditor)
with zero framework dependencies (no Mesa, no Solara).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from compute_permit_sim.core.agents import Lab
from compute_permit_sim.core.enforcement import Auditor
from compute_permit_sim.core.market import SimpleClearingMarket
from compute_permit_sim.schemas import ScenarioConfig


@dataclass
class AgentOutcome:
    """Per-agent results from one step of the game loop."""

    lab_id: int
    permits_allocated: int = 0  # Permits received from market this step
    audited: bool = False  # Was an audit triggered for this lab?
    caught: bool = False  # Caught by any detection channel?
    caught_backcheck: bool = False  # Was the backcheck specifically involved?
    penalty: float = 0.0
    collateral_seized: bool = False
    ran: bool = False  # Did the lab run its training this step?
    realized_excess: float = 0.0  # Unpermitted FLOPs run (0 if compliant)


@dataclass
class StepOutcome:
    """Aggregate results from one step of the game loop."""

    clearing_price: float = 0.0
    agent_outcomes: dict[int, AgentOutcome] = field(default_factory=dict)


def execute_step(
    labs: list[Lab],
    market: SimpleClearingMarket,
    auditor: Auditor,
    config: ScenarioConfig,
    rng: random.Random | None = None,
) -> StepOutcome:
    """Execute one step of the simulation game loop.

    Args:
        labs: Domain Lab objects (mutated in place for compliance state).
        market: Market mechanism instance.
        auditor: Auditor/enforcement instance.
        config: Full scenario configuration.
        rng: Seeded RNG for audit rolls and capacity sampling.

    Returns:
        StepOutcome with per-agent audit results.
    """
    _rng = rng or random.Random()
    outcome = StepOutcome()

    flop_threshold = config.flop_threshold
    flops_per_permit = config.market.flops_per_permit
    p_w = config.audit.whistleblower_prob
    p_m = config.audit.monitoring_prob

    # Initialise per-agent outcome tracking
    for lab in labs:
        outcome.agent_outcomes[lab.lab_id] = AgentOutcome(lab_id=lab.lab_id)

    # Partition labs: above vs below the regulatory threshold
    above = [lab for lab in labs if lab.planned_training_flops > flop_threshold]
    below = [lab for lab in labs if lab.planned_training_flops <= flop_threshold]

    # Below-threshold labs run freely: no permits, no enforcement
    for lab in below:
        outcome.agent_outcomes[lab.lab_id].ran = True

    # ------------------------------------------------------------------
    # Phase 0 — Collateral (above-threshold labs only)
    # ------------------------------------------------------------------
    collateral_k = config.collateral_amount
    if collateral_k > 0:
        for lab in above:
            lab.collateral_posted = collateral_k

    # ------------------------------------------------------------------
    # Phase 1 — Trading (above-threshold labs only)
    # ------------------------------------------------------------------
    clearing_price = 0.0
    if above:
        if flops_per_permit is None:
            # Binary mode: each lab bids for exactly 1 permit
            bids = [(lab.lab_id, 1, lab.get_bid()) for lab in above]
        else:
            # FLOP mode: bid for enough permits to cover the full planned run
            bids = []
            for lab in above:
                qty = max(1, math.ceil(lab.planned_training_flops / flops_per_permit))
                bid_per = lab.economic_value / qty
                bids.append((lab.lab_id, qty, bid_per))

        clearing_price, allocations = market.allocate(bids)
        outcome.clearing_price = clearing_price

        for lab in above:
            lab.permits_held = allocations.get(lab.lab_id, 0)
            outcome.agent_outcomes[lab.lab_id].permits_allocated = lab.permits_held

    # ------------------------------------------------------------------
    # Phase 2 — Compliance decisions (above-threshold labs with excess)
    # ------------------------------------------------------------------
    for lab in above:
        excess = lab.excess_flops(flops_per_permit)
        if excess <= 0:
            # Case 2: fully permitted — auto-compliant, runs legally
            lab.is_compliant = True
            continue

        # Case 3 or 4: excess > 0 — firm runs the deterrence calculation.
        # Firm uses the same combined detection model as the auditor,
        # including contributions from whistleblower and monitoring.
        p_detection = auditor.compute_detection_probability(
            excess_compute=excess,
            flop_threshold=flop_threshold,
            audit_coefficient=lab.current_audit_coefficient,
            p_w=p_w,
            p_m=p_m,
        )
        lab.decide_compliance(
            market_price=clearing_price,
            penalty=lab.penalty_amount,
            detection_prob=p_detection,
        )

    # Compute realized_excess for every lab after compliance decisions
    for lab in labs:
        ao = outcome.agent_outcomes[lab.lab_id]
        if lab.planned_training_flops <= flop_threshold:
            # Case 1: below threshold — runs freely, no excess
            ao.realized_excess = 0.0
            ao.ran = True
        else:
            excess = lab.excess_flops(flops_per_permit)
            if excess <= 0:
                # Case 2: fully permitted — runs legally
                ao.realized_excess = 0.0
                ao.ran = True
            elif lab.is_compliant:
                # Case 4: deterred — chose not to run
                ao.realized_excess = 0.0
                ao.ran = False
            else:
                # Case 3: cheating — ran with unpermitted excess
                ao.realized_excess = excess
                ao.ran = True

    # ------------------------------------------------------------------
    # Phase 3–4 — Enforcement (above-threshold labs only)
    #
    # Detection channels are combined within the audit event:
    #   - Direct audit pass (1 - FNR)
    #   - Backcheck (FNR × backcheck_prob, if direct missed)
    #   - Whistleblower (p_w, independent within audit)
    #   - Monitoring (p_m, independent within audit)
    #
    # Audit occurrence is subject to max_audits_per_step budget cap.
    # ------------------------------------------------------------------
    lab_by_id = {lab.lab_id: lab for lab in labs}

    # Determine which labs trigger an audit, tracking signal for prioritisation
    potential_audits: list[tuple[int, float]] = []  # (lab_id, signal)
    for lab in above:
        ao = outcome.agent_outcomes[lab.lab_id]
        signal = auditor.compute_signal(ao.realized_excess, flop_threshold)
        p_audit = auditor.compute_audit_probability(
            signal=signal,
            audit_coefficient=lab.current_audit_coefficient,
        )
        if _rng.random() < p_audit:
            potential_audits.append((lab.lab_id, signal))

    # Apply audit capacity constraint
    max_audits = config.audit.max_audits_per_step
    if max_audits is not None and len(potential_audits) > max_audits:
        if config.audit.signal_dependent:
            # Rational regulator: prioritise labs with the highest signals
            potential_audits.sort(key=lambda x: x[1], reverse=True)
            actual_audit_ids = [lab_id for lab_id, _ in potential_audits[:max_audits]]
        else:
            # Signal-blind: random sample among triggered labs
            actual_audit_ids = [
                lab_id for lab_id, _ in _rng.sample(potential_audits, max_audits)
            ]
    else:
        actual_audit_ids = [lab_id for lab_id, _ in potential_audits]

    actual_audit_set = set(actual_audit_ids)

    # Execute audits: all detection channels resolved together
    for lab_id in actual_audit_ids:
        lab = lab_by_id[lab_id]
        ao = outcome.agent_outcomes[lab_id]
        ao.audited = True

        is_actually_compliant = ao.realized_excess <= 0
        caught, caught_backcheck = auditor.audit_detection_channel(
            is_actually_compliant, p_w=p_w, p_m=p_m
        )

        if caught and not is_actually_compliant:
            ao.caught = True
            ao.caught_backcheck = caught_backcheck
            ao.penalty = lab.penalty_amount

            if lab.collateral_posted > 0:
                ao.collateral_seized = True
                lab.collateral_posted = 0.0

            lab.on_audit_failure(audit_escalation=config.audit.audit_escalation)

    # Mark non-audited above-threshold labs explicitly
    for lab in above:
        if lab.lab_id not in actual_audit_set:
            outcome.agent_outcomes[lab.lab_id].audited = False

    # Refund collateral for labs that were not caught
    if collateral_k > 0:
        for lab in labs:
            if lab.collateral_posted > 0:
                lab.collateral_posted = 0.0

    # ------------------------------------------------------------------
    # Phase 5 — Value realization
    # Labs that ran earn economic_value. Tracked via ao.ran.
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Phase 6 — Dynamic factor updates
    # ------------------------------------------------------------------
    audit_decay = config.audit.audit_decay_rate
    for lab in labs:
        lab.decay_audit_coefficient(audit_decay)

        # Accumulate capability for labs that ran this step
        if outcome.agent_outcomes[lab.lab_id].ran:
            lab.cumulative_capability += 1.0

    if labs:
        mean_cap = sum(lab.cumulative_capability for lab in labs) / len(labs)
        for lab in labs:
            lab.update_racing_factor(mean_cap)

    return outcome
