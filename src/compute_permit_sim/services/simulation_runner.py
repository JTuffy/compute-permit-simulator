"""Single-run headless simulation runner.

Executes one complete simulation run synchronously, collecting all step
data into a ``SimulationRun``.  No UI imports or reactive state.

Shared by:
  - ``vis/simulation.py``  (basic panel click → background thread)
  - Potentially other callers that need a packed run without UI.

>>> from compute_permit_sim.services.simulation_runner import run_single
>>> run = run_single(config)
>>> run.metrics.final_compliance
"""

from __future__ import annotations

import base64
import hashlib
import json
import time

from compute_permit_sim.schemas import (
    MarketSnapshot,
    RunMetrics,
    SimulationRun,
    StepResult,
)
from compute_permit_sim.schemas.config import ScenarioConfig
from compute_permit_sim.services.mesa_model import ComputePermitModel
from compute_permit_sim.services.metrics import calculate_compliance


def run_single(config: ScenarioConfig) -> SimulationRun:
    """Run all steps for *config* and return a packed ``SimulationRun``.

    Args:
        config: Fully-resolved scenario config (seed already set).

    Returns:
        A ``SimulationRun`` with ``steps``, ``metrics``, and stable identifiers.
    """
    model = ComputePermitModel(config=config)

    steps: list[StepResult] = []
    compliance_history: list[float] = []

    for step_num in range(1, config.steps + 1):
        model.step()

        agents = model.get_agent_snapshots()
        compliance = calculate_compliance(agents)
        compliance_history.append(compliance)

        steps.append(
            StepResult(
                step=step_num,
                market=MarketSnapshot(
                    price=model.market.current_price,
                    supply=model.market.max_supply,
                ),
                agents=agents,
                audit=[],
            )
        )

    # Final metrics
    final_compliance = compliance_history[-1] if compliance_history else 0.0
    avg_compliance = (
        sum(compliance_history) / len(compliance_history) if compliance_history else 0.0
    )
    final_price = model.market.current_price

    # Stable ID / URL token from config (exclude defaults to keep compact)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_state = config.model_dump(exclude_defaults=True, exclude_none=True)
    json_bytes = json.dumps(run_state, sort_keys=True).encode("utf-8")
    short_hash = hashlib.sha256(json_bytes).hexdigest()[:8]
    url_id = base64.b64encode(json.dumps(run_state).encode("utf-8")).decode("utf-8")

    return SimulationRun(
        id=f"run_{timestamp}",
        sim_id=short_hash,
        url_id=url_id,
        config=config,
        steps=steps,
        metrics=RunMetrics(
            final_compliance=final_compliance,
            final_price=final_price,
            deterrence_success_rate=avg_compliance,
        ),
    )
