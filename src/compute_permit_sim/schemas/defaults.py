"""Default parameter values for the Compute Permit Simulator.

These constants are used as `Field(default=...)` values in the Pydantic
config schemas.  They live here (in the schemas layer) rather than in
`core/constants.py` so that `schemas` does not depend on `core`.

All monetary values are in MILLIONS OF USD (M$).  See the companion
design notes below for empirical references.
"""

# =============================================================================
# UNIT SCALING REFERENCE
# =============================================================================
# All monetary values are in MILLIONS OF USD (M$).
#
# This scaling is based on empirical data from frontier AI development:
#
# TRAINING RUN COSTS (economic_value):
#   - GPT-4 (2023): ~$40M amortized hardware + energy
#   - Gemini Ultra (2023): ~$30M
#   - Current frontier (2024-2025): ~$100-500M
#   - Projected (2026-2027): ~$1,000M ($1B)
#   Sources:
#     - Epoch AI, "How much does it cost to train frontier AI models?" (2024)
#       https://epoch.ai/blog/how-much-does-it-cost-to-train-frontier-ai-models
#     - Cottier & Rahman, "The rising costs of training frontier AI models"
#       arXiv:2405.21015 (2024)
#
# PENALTY AMOUNTS:
#   - EU AI Act: up to €35M (~$38M) or 7% of global turnover
#   - For major labs (revenue ~$1-10B), 7% = $70-700M
#   Sources:
#     - EU AI Act Article 99, https://artificialintelligenceact.eu/article/99/
#
# REPUTATION COSTS:
#   - Estimated at 10-50% of training run value for reputational damage
#   - Major safety incident could cost $50-500M in lost partnerships/trust
#
# Default scenario represents a near-future frontier regime (~2025-2026).
# =============================================================================

# --- Regulatory Threshold ---
# FLOP-based threshold: training runs require permits when
# planned_training_flops > flop_threshold.
# Signal strength for enforcement scales with excess above this threshold.
#
# FLOP SCALING REFERENCE:
#   10^23 FLOP: GPT-3 scale (~$5M)
#   10^24 FLOP: GPT-4 scale (~$50M)
#   10^25 FLOP: Near-future frontier (~$500M)
#   10^26 FLOP: Projected 2027 frontier (~$5B)
#   Sources:
#     - Epoch AI, "Compute Trends Across Three Eras of ML" (2022)
#     - EU AI Act recital: 10^25 FLOP as "high-impact" threshold
DEFAULT_FLOP_THRESHOLD = 1e25  # FLOP: near-future frontier threshold
DEFAULT_LAB_COMPUTE_CAPACITY_MIN = 1e24  # FLOP: small frontier run
DEFAULT_LAB_COMPUTE_CAPACITY_MAX = 1e26  # FLOP: large frontier run

# --- Audit Policy Defaults ---
#
# Stage 1: AUDIT OCCURRENCE — what causes an audit?
#   p_audit = min(1.0, (base_prob + signal × (1.0 - base_prob)) × c(i))
#   where signal = min(1.0, (excess / threshold)^signal_exponent)
#   Signal-dependent auditing must be enabled (signal_dependent=True) for
#   signal to affect audit rates.  When off, all firms face base_prob × c(i).
DEFAULT_AUDIT_BASE_PROB = 0.05  # pi_0: baseline audit rate for all firms
DEFAULT_SIGNAL_DEPENDENT = False  # False = pure random auditing; True = signal-driven
# Signal exponent controls how excess compute maps to suspicion signal:
#   signal = min(1.0, (excess_compute / flop_threshold) ^ signal_exponent)
#   exponent=1.0 (linear): 50% excess → 50% signal, 100% excess → 100% signal
#   exponent=0.5 (concave/sqrt): small excess already moderately detectable
#     e.g. 25% excess → 50% signal, harder to hide even small violations
#   exponent=2.0 (convex/quadratic): small excess nearly invisible
#     e.g. 50% excess → 25% signal, only very large excess is obvious
#   Intuition: lower exponent = stricter regime (hard to hide anything),
#              higher exponent = lenient regime (only flagrant violations visible)
DEFAULT_SIGNAL_EXPONENT = 1.0
#
# Stage 2: AUDIT OUTCOME — given audit, does it find a violation?
#   p_catch_if_audited = (1 - FNR) + FNR × backcheck_prob
DEFAULT_AUDIT_FALSE_POS_RATE = 0.0  # alpha: P(false alarm | compliant firm audited)
DEFAULT_AUDIT_FALSE_NEG_RATE = 0.40  # beta: 40% miss rate in Lawless env
# Penalty structure:
DEFAULT_AUDIT_PENALTY_AMOUNT = 200.0  # M$: flat penalty (default/fallback)
DEFAULT_AUDIT_BACKCHECK_PROB = 0.0  # p_b: historical audit discovery rate
DEFAULT_AUDIT_WHISTLEBLOWER_PROB = 0.0  # p_w: whistleblower detection rate
DEFAULT_AUDIT_MONITORING_PROB = (
    0.0  # p_m: global monitoring (hardware/electricity metering)
)

# --- Collateral/Staking Defaults ---
# Collateral is a refundable deposit posted before bidding.
# Seized on verified violation; returned otherwise. 0 = disabled.
# Reference: Christoph (2026) Section 2.5, Proposition 3
#   P_eff = min(K + phi, L) where K = collateral, phi = ex post fine, L = liability
DEFAULT_COLLATERAL_AMOUNT = 0.0  # M$: Lawless = 0 collateral

# --- Market Defaults ---
DEFAULT_MARKET_PERMIT_CAP = 20.0  # Number of permits available
DEFAULT_MARKET_FIXED_PRICE = 70.0  # M$: Lawless implied delta C
DEFAULT_FLOPS_PER_PERMIT = (
    None  # None = binary (0/1 per firm); float = FLOP-denominated
)

# --- Lab Agent Defaults ---
# Economic value: value of a frontier training run (M$)
DEFAULT_LAB_ECON_VALUE_MIN = 50.0  # M$: lower-tier frontier run
DEFAULT_LAB_ECON_VALUE_MAX = 200.0  # M$: high-value frontier run
# Risk profile: multiplier on perceived penalty (dimensionless)
DEFAULT_LAB_RISK_PROFILE_MIN = 1.0  # risk-seeking
DEFAULT_LAB_RISK_PROFILE_MAX = 1.0  # risk-averse
# Capability value: strategic value of model capabilities (M$)
DEFAULT_LAB_CAPABILITY_VALUE = 0.0  # V_b: baseline capability premium
# Racing factor: urgency multiplier (dimensionless)
DEFAULT_LAB_RACING_FACTOR = 1.0  # c_r: 1.0 = no racing pressure
# Reputation sensitivity: perceived reputation cost if caught (M$)
DEFAULT_LAB_REPUTATION_SENSITIVITY = 0.0  # R: brand/trust damage
# Audit coefficient: firm-specific audit rate scaling (dimensionless)
DEFAULT_LAB_AUDIT_COEFFICIENT = 0.8  # c(i): Lawless = 0.8 evasion factor
# --- Dynamic Factor Defaults ---
# All default to 0.0 (static behavior). Set > 0 to activate.
#
# 4.1 Reputation damage accumulation
# Each failed audit multiplies reputation by (1 + escalation_factor)
# Formula: reputation_t = base_rep × (1 + factor)^failed_audits
DEFAULT_REPUTATION_ESCALATION_FACTOR = 0.0  # 0 = static; 0.5 = +50% per failure

# 4.2 Audit rate escalation & decay
# Failed audit increases audit_coefficient; decays back to 1.0 over time
# Formula: coeff_t = 1.0 + (coeff_{t-1} - 1.0) × decay + escalation_if_caught
DEFAULT_AUDIT_ESCALATION = 0.0  # 0 = static; 1.0 = +1.0 per failure
DEFAULT_AUDIT_DECAY_RATE = 0.8  # per-step decay (0.8 = 20% decay toward 1.0)

# 4.3 Racing factor dynamics
# Racing factor depends on relative capability position
# Formula: racing_t = base_racing × (1 + gap_sensitivity × gap / scale)
DEFAULT_RACING_GAP_SENSITIVITY = 0.0  # 0 = static; 0.5 = moderate dynamics
DEFAULT_CAPABILITY_SCALE = 100.0  # normalization for capability gap

# --- Scenario Defaults ---
DEFAULT_SCENARIO_N_AGENTS = 10  # Constraint: Max 20
DEFAULT_SCENARIO_STEPS = 10  # Constraint: Max 10
