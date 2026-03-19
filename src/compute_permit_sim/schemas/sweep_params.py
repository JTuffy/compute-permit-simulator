"""Registry of sweepable simulation parameters.

Provides a typed ``SweepParam`` descriptor for every parameter that can be
varied in a 1D parameter sweep, along with helpers to:

- Look up a param by dot-path (``get_param``)
- Generate a list of sweep values from min/max/step (``generate_values``)
- Drive the UI dropdown + range inputs in the Batch panel

Units
-----
All monetary values are in M$ (millions of USD), consistent with defaults.py.
Probabilities are dimensionless [0, 1].
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SweepParam:
    """Descriptor for one sweepable configuration parameter."""

    path: str  # dot-path into ScenarioConfig, e.g. "audit.base_prob"
    label: str  # human-readable label, e.g. "Base Audit Rate π₀"
    unit: str  # display unit: "probability" | "M$" | "count" | ""
    default_min: float
    default_max: float
    default_step: float
    description: str
    category: str  # grouping label for the UI dropdown


# ---------------------------------------------------------------------------
# Canonical registry
# ---------------------------------------------------------------------------

SWEEPABLE_PARAMS: list[SweepParam] = [
    # --- Enforcement ---
    SweepParam(
        path="audit.base_prob",
        label="Base Audit Rate π₀",
        unit="probability",
        default_min=0.01,
        default_max=0.30,
        default_step=0.05,
        description="Baseline probability that any above-threshold lab is audited each step.",
        category="Enforcement",
    ),
    SweepParam(
        path="audit.false_negative_rate",
        label="False Negative Rate β",
        unit="probability",
        default_min=0.0,
        default_max=0.8,
        default_step=0.1,
        description="Probability that an audit misses a genuine violation.",
        category="Enforcement",
    ),
    SweepParam(
        path="audit.monitoring_prob",
        label="Monitoring Probability p_m",
        unit="probability",
        default_min=0.0,
        default_max=1.0,
        default_step=0.1,
        description="Passive monitoring detection probability (e.g. hardware metering).",
        category="Enforcement",
    ),
    SweepParam(
        path="audit.whistleblower_prob",
        label="Whistleblower Probability p_w",
        unit="probability",
        default_min=0.0,
        default_max=0.5,
        default_step=0.05,
        description="Probability of whistleblower detection per step.",
        category="Enforcement",
    ),
    SweepParam(
        path="audit.penalty_amount",
        label="Penalty φ",
        unit="M$",
        default_min=0.0,
        default_max=500.0,
        default_step=50.0,
        description="Ex-post fine levied on caught violators.",
        category="Enforcement",
    ),
    SweepParam(
        path="audit.audit_escalation",
        label="Audit Escalation Factor",
        unit="",
        default_min=0.0,
        default_max=2.0,
        default_step=0.25,
        description="Increase in audit coefficient per failed audit (0 = static).",
        category="Enforcement",
    ),
    SweepParam(
        path="audit.audit_decay_rate",
        label="Audit Decay Rate",
        unit="probability",
        default_min=0.0,
        default_max=1.0,
        default_step=0.1,
        description="Per-step decay of elevated audit coefficient back to baseline.",
        category="Enforcement",
    ),
    # --- Economics ---
    SweepParam(
        path="collateral_amount",
        label="Collateral K",
        unit="M$",
        default_min=0.0,
        default_max=150.0,
        default_step=15.0,
        description="Refundable deposit posted before market participation; seized on violation.",
        category="Economics",
    ),
    SweepParam(
        path="market.fixed_price",
        label="Fixed Permit Price p̄",
        unit="M$",
        default_min=0.5,
        default_max=100.0,
        default_step=10.0,
        description="Fixed permit price (None = competitive auction).",
        category="Economics",
    ),
    SweepParam(
        path="market.permit_cap",
        label="Permit Supply Cap Q",
        unit="count",
        default_min=1.0,
        default_max=20.0,
        default_step=1.0,
        description="Number of permits available each step.",
        category="Economics",
    ),
    # --- Agents ---
    SweepParam(
        path="n_agents",
        label="Number of Firms N",
        unit="count",
        default_min=5.0,
        default_max=30.0,
        default_step=5.0,
        description="Total number of AI lab agents in the simulation.",
        category="Agents",
    ),
    SweepParam(
        path="lab.economic_value_max",
        label="Max Firm Economic Value",
        unit="M$",
        default_min=50.0,
        default_max=500.0,
        default_step=50.0,
        description="Upper bound of the uniform draw for each firm's training run value.",
        category="Agents",
    ),
    SweepParam(
        path="lab.risk_profile_max",
        label="Max Risk Profile",
        unit="",
        default_min=0.5,
        default_max=3.0,
        default_step=0.25,
        description="Upper bound of risk appetite multiplier (>1 = risk-seeking).",
        category="Agents",
    ),
    SweepParam(
        path="lab.capability_value",
        label="Capability Race Premium V_b",
        unit="M$",
        default_min=0.0,
        default_max=300.0,
        default_step=20.0,
        description="Strategic value of model capabilities from training (arms-race premium added to gain from cheating).",
        category="Agents",
    ),
    SweepParam(
        path="lab.racing_factor",
        label="Racing Factor c_r",
        unit="",
        default_min=0.0,
        default_max=5.0,
        default_step=0.25,
        description="Urgency multiplier on capability value; higher = stronger competitive pressure to cheat.",
        category="Agents",
    ),
    SweepParam(
        path="lab.reputation_escalation_factor",
        label="Reputation Escalation Factor",
        unit="",
        default_min=0.0,
        default_max=5.0,
        default_step=0.25,
        description="Per-violation multiplier on reputation cost: rep_t = base × (1+factor)^n_caught. 0 = no escalation.",
        category="Agents",
    ),
    SweepParam(
        path="lab.reputation_sensitivity",
        label="Reputation Sensitivity R",
        unit="M$",
        default_min=0.0,
        default_max=100.0,
        default_step=5.0,
        description="Base reputation cost per violation (M$). Compounds with reputation_escalation_factor.",
        category="Agents",
    ),
    # --- Dynamics ---
    SweepParam(
        path="audit.signal_exponent",
        label="Signal Exponent",
        unit="",
        default_min=0.25,
        default_max=3.0,
        default_step=0.25,
        description="Controls how excess compute maps to detection signal (1=linear, <1=concave, >1=convex).",
        category="Dynamics",
    ),
]


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

_PARAM_BY_PATH: dict[str, SweepParam] = {p.path: p for p in SWEEPABLE_PARAMS}
_PARAMS_BY_CATEGORY: dict[str, list[SweepParam]] = {}
for _p in SWEEPABLE_PARAMS:
    _PARAMS_BY_CATEGORY.setdefault(_p.category, []).append(_p)
del _p  # avoid leaking the loop variable into module namespace


def get_param(path: str) -> SweepParam:
    """Look up a SweepParam by its dot-path.

    Args:
        path: Config dot-path, e.g. ``"audit.base_prob"``.

    Returns:
        Matching ``SweepParam``.

    Raises:
        KeyError: if path is not in the registry.
    """
    if path not in _PARAM_BY_PATH:
        raise KeyError(
            f"'{path}' is not a registered sweepable parameter. "
            f"Available: {sorted(_PARAM_BY_PATH)}"
        )
    return _PARAM_BY_PATH[path]


def categories() -> list[str]:
    """Return all category names in registry order."""
    return list(_PARAMS_BY_CATEGORY.keys())


def params_for_category(category: str) -> list[SweepParam]:
    """Return all SweepParams for a given category."""
    return _PARAMS_BY_CATEGORY.get(category, [])


def generate_values(
    param: SweepParam,
    min_val: float | None = None,
    max_val: float | None = None,
    step: float | None = None,
) -> list[float]:
    """Generate a list of sweep values for a parameter.

    Falls back to the param's defaults for any omitted argument.

    Args:
        param: The ``SweepParam`` to generate values for.
        min_val: Start of the sweep range (inclusive).
        max_val: End of the sweep range (inclusive).
        step: Interval between points.

    Returns:
        Sorted list of float values from min_val to max_val at given step,
        always including max_val if it falls within tolerance.
    """
    lo = min_val if min_val is not None else param.default_min
    hi = max_val if max_val is not None else param.default_max
    dx = step if step is not None else param.default_step

    if dx <= 0:
        raise ValueError(f"Step must be positive, got {dx}")
    if lo > hi:
        raise ValueError(f"min_val ({lo}) must be <= max_val ({hi})")

    n_steps = int(round((hi - lo) / dx))
    values = [lo + i * dx for i in range(n_steps + 1)]

    # Clamp final value to hi if floating-point drift pushed it slightly over
    if values and abs(values[-1] - hi) > dx * 0.01:
        if values[-1] > hi:
            values = values[:-1]
        values.append(hi)

    # Round to 8 decimal places to avoid floating-point noise in display
    return [round(v, 8) for v in values]
