"""Core game loop — pure business logic for one simulation step.

Orchestrates the six-phase turn sequence:
    0. Collateral posting
    1. Trading (bids + market allocation)
    2. Compliance decisions
    3–4. Signal generation, audits, enforcement
    5. Value realization
    6. Dynamic factor updates (decay, racing)

All functions operate on domain objects (Lab, SimpleClearingMarket, Auditor)
with zero framework dependencies (no Mesa, no Solara).
"""

from __future__ import annotations

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
    wealth_delta: float = 0.0
    audited: bool = False
    caught: bool = False
    penalty: float = 0.0
    collateral_seized: bool = False


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
        rng: Seeded RNG for audit capacity sampling.

    Returns:
        StepOutcome with per-agent wealth deltas and audit results.
    """
    outcome = StepOutcome()

    # Initialize per-agent outcome tracking
    for lab in labs:
        outcome.agent_outcomes[lab.lab_id] = AgentOutcome(lab_id=lab.lab_id)

    # Phase 0: Collateral
    collateral_k = config.collateral_amount
    if collateral_k > 0:
        for lab in labs:
            lab.collateral_posted = collateral_k
            outcome.agent_outcomes[lab.lab_id].wealth_delta -= collateral_k

    # Phase 1: Trading
    bids = [(lab.lab_id, lab.get_bid()) for lab in labs]
    clearing_price, winning_ids = market.allocate(bids)
    outcome.clearing_price = clearing_price

    winning_set = set(winning_ids)
    for lab in labs:
        if lab.lab_id in winning_set:
            lab.has_permit = True
            outcome.agent_outcomes[lab.lab_id].wealth_delta -= clearing_price
        else:
            lab.has_permit = False

    # Phase 2: Compliance decisions
    flop_threshold = config.flop_threshold
    for lab in labs:
        hypothetical_usage = lab.planned_training_flops
        expected_signal = auditor.compute_signal_strength(
            used_compute=hypothetical_usage,
            flop_threshold=flop_threshold,
            is_compliant=False,
        )
        detection_prob_audit = auditor.compute_effective_detection(
            audit_coefficient=lab.current_audit_coefficient,
            signal_strength=expected_signal,
        )
        p_wb = config.audit.whistleblower_prob
        detection_prob = 1.0 - (1.0 - detection_prob_audit) * (1.0 - p_wb)

        firm_penalty = auditor.compute_penalty_amount(firm_value=lab.firm_revenue)
        lab.decide_compliance(
            market_price=clearing_price,
            penalty=firm_penalty,
            detection_prob=detection_prob,
        )

    # Phase 3–4: Signal generation, audit decisions, enforcement
    potential_audit_ids: list[int] = []
    lab_by_id = {lab.lab_id: lab for lab in labs}

    for lab in labs:
        did_run = lab.has_permit or not lab.is_compliant
        used_compute = lab.planned_training_flops if did_run else 0.0

        signal_strength = auditor.generate_signal(
            used_compute=used_compute,
            flop_threshold=flop_threshold,
            is_compliant=lab.is_compliant,
        )
        if auditor.decide_audit(signal_strength):
            potential_audit_ids.append(lab.lab_id)

    # Apply audit capacity constraint
    if config.audit.max_audits_per_step is not None:
        if len(potential_audit_ids) > config.audit.max_audits_per_step:
            actual_rng = rng or random.Random()
            actual_audit_ids = actual_rng.sample(
                potential_audit_ids, config.audit.max_audits_per_step
            )
        else:
            actual_audit_ids = potential_audit_ids
    else:
        actual_audit_ids = potential_audit_ids

    actual_audit_set = set(actual_audit_ids)

    # Execute audits
    for lab_id in actual_audit_ids:
        lab = lab_by_id[lab_id]
        ao = outcome.agent_outcomes[lab_id]
        ao.audited = True

        effective_compliant = lab.is_compliant or lab.has_permit
        violation_found = auditor.audit_finds_violation(effective_compliant)

        if violation_found and not lab.has_permit:
            penalty = auditor.apply_penalty(
                violation_found=True, firm_value=lab.firm_revenue
            )
            ao.wealth_delta -= penalty
            ao.caught = True
            ao.penalty = penalty

            if lab.collateral_posted > 0:
                ao.collateral_seized = True
                lab.collateral_posted = 0.0

            lab.on_audit_failure(
                audit_escalation=config.audit.audit_escalation,
            )

    # Mark non-audited agents
    for lab in labs:
        if lab.lab_id not in actual_audit_set:
            ao = outcome.agent_outcomes[lab.lab_id]
            ao.audited = False

    # Refund collateral for agents not caught
    if collateral_k > 0:
        for lab in labs:
            if lab.collateral_posted > 0:
                outcome.agent_outcomes[lab.lab_id].wealth_delta += lab.collateral_posted
                lab.collateral_posted = 0.0

    # Phase 5: Value realization
    for lab in labs:
        if lab.has_permit or not lab.is_compliant:
            outcome.agent_outcomes[lab.lab_id].wealth_delta += lab.economic_value

    # Phase 6: Dynamic factor updates
    audit_decay = config.audit.audit_decay_rate
    for lab in labs:
        lab.decay_audit_coefficient(audit_decay)

    capabilities = [lab.cumulative_capability for lab in labs]
    if capabilities:
        mean_cap = sum(capabilities) / len(capabilities)
        for lab in labs:
            lab.update_racing_factor(mean_cap)

    return outcome
