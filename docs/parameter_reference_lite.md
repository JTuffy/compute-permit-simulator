# Parameter Reference — Lite

All monetary values in **M$ (millions USD)**. Defaults based on a near-future frontier AI regulation scenario (~2025-2026).

---

## Scenario (`ScenarioConfig`)

- **`n_agents`** *(default: 20)* — Number of labs in the simulation. More agents creates stiffer permit competition, driving prices up.
- **`steps`** *(default: 10)* — How many turns run. Dynamic factors (reputation, escalation, racing) compound over time, so longer runs amplify their effects.
- **`flop_threshold`** *(default: 1e25 FLOP)* — Compute threshold above which labs must hold permits. Determines how *visible* a violation is: labs running just above the threshold emit weak signals; those running 2× above are fully visible.
- **`collateral_amount`** *(default: 0 M$)* — Refundable deposit posted each step. Seized if caught. Makes the threat of punishment credible even if labs have limited assets. `0` disables it.

---

## Audit Policy (`AuditConfig`)

### Detection Mechanics

- **`base_prob` (π₀)** *(default: 5%)* — Baseline audit rate for all firms each step, regardless of behaviour. Raises the floor on detection even for careful violators.
- **`high_prob` (π₁)** *(default: 0%)* — Maximum audit probability, reached when a lab emits a maximum-strength signal. Linearly interpolated with `base_prob` based on compute excess. Default `0%` disables signal-responsive targeting.
- **`false_negative_rate` (β)** *(default: 40%)* — Chance an audit *misses* a real violation. Directly reduces effective detection probability in the deterrence equation. Higher β → audits are less reliable → more labs cheat.
- **`false_positive_rate` (α)** *(default: 10%)* — Chance a compliant lab is flagged. Currently only affects reporting (no penalty on false positives), so minimal simulation impact.
- **`backcheck_prob` (p_b)** *(default: 10%)* — Independent chance of catching a violation through historical review. Adds a detection floor that persists even when realtime audits miss. **Also raises the perceived detection probability labs use when deciding to cheat.**
- **`whistleblower_prob` (p_w)** *(default: 5%)* — Independent detection channel. Combined multiplicatively with audit detection in the deterrence calculation.
- **`max_audits_per_step`** *(default: None)* — Hard cap on audits per turn. Models budget-constrained regulators. When hit, auditors are randomly sampled from flagged labs. Note: `cost` (below) does not feed back into this cap.

### Penalty Structure

- **`penalty_amount`** *(default: 200 M$)* — Flat fallback penalty. Used when neither `penalty_fixed` nor `penalty_percentage` are configured.
- **`penalty_fixed`** *(default: 0 M$)* — Fixed penalty floor. Activates the flexible penalty system when `> 0`. Models EU AI Act €35M floor.
- **`penalty_percentage`** *(default: 0%)* — Revenue-proportional penalty. `penalty = max(penalty_fixed, penalty_percentage × firm_revenue)`. Models EU AI Act 7% turnover rule.
- **`penalty_ceiling`** *(default: None)* — Hard cap on any computed penalty. Models limited liability — labs cannot lose more than this cap.
- **`cost`** *(default: 0.5 M$)* — Regulator's cost per audit. Tracked as `total_enforcement_cost` in outputs. **No effect on lab decisions or audit counts.**

### Dynamic Factors

- **`audit_escalation`** *(default: 0)* — Amount added to a caught lab's audit coefficient per failure. Makes repeat violators increasingly visible/targeted. `0` = disabled.
- **`audit_decay_rate`** *(default: 0.8)* — Rate at which escalated audit targeting decays back to baseline each step. `0.8` = 20% decay per step. Only active if `audit_escalation > 0`.

---

## Market (`MarketConfig`)

- **`token_cap`** *(default: 20)* — Total permits available. Sets scarcity: when `n_agents > token_cap`, competition arises and prices rise. The clearing price is the Qth highest bid. Lower `token_cap` = higher prices = stronger financial motive to cheat.
- **`fixed_price`** *(default: 70 M$)* — If set, replaces the competitive auction with a fixed price and unlimited supply. Labs whose `economic_value >= fixed_price` buy a permit; others must decide whether to cheat. Set to `None` to use the competitive auction.

---

## Lab Agent Generation (`LabConfig`)

Each lab's individual value is sampled from `uniform(min, max)` at simulation start.

### Economic Incentives

- **`economic_value_min/max`** *(default: 50–200 M$)* — Value `v_i` each lab gains from a successful training run. Drives both bidding in the permit market and the financial motive to cheat. Also the actual wealth gain when a lab runs (Phase 5). Currently independent of `planned_training_flops`.
- **`capability_value` (V_b)** *(default: 20 M$)* — Strategic value of training, independent of commercial revenue. Adds to the motive to cheat even if the lab can't afford a permit. Shared across all labs (not per-lab). Only affects the compliance decision — does **not** accrue to actual wealth.
- **`racing_factor` (c_r)** *(default: 1.0)* — Urgency multiplier on `capability_value`. Models competitive pressure: `strategic_gain = racing_factor × capability_value`. Higher = stronger non-financial motive to cheat.

### Risk & Compliance Behaviour

- **`risk_profile_min/max`** *(default: 0.8–1.2)* — Per-lab multiplier on perceived punishment. `> 1` = risk-averse (overestimates penalty); `< 1` = risk-seeking (discounts penalty). Key driver of behavioural diversity across labs.
- **`reputation_sensitivity` (R)** *(default: 50 M$)* — Perceived brand/trust damage if caught. Added alongside the direct financial penalty in the deterrence calculation.
- **`audit_coefficient` c(i)** *(default: 0.8)* — Firm-specific scaling on audit probability. `0.8` means the lab perceives only 80% of the base detection probability (reflects evasion skill or opacity). Can escalate after repeated violations.

### Revenue & Compute

- **`firm_revenue_min/max`** *(default: 500–5000 M$)* — Lab's annual revenue. Used to compute revenue-proportional penalties. Only matters when `penalty_percentage > 0`.
- **`training_flops_min/max`** *(default: 1e24–1e26 FLOP)* — Planned training run size, fixed at lab creation and used every step. Compared to `flop_threshold` to determine permit requirement and enforcement signal strength.

### Capacity (Currently Unused in Simulation Logic)

- **`capacity_min/max`** *(default: 1.0–2.0)* — Intended to represent a lab's physical compute ceiling. Currently stored per-lab but **not used in any compliance, market, or enforcement calculation**. Units are arbitrary (not FLOP), and the parameter does not constrain `training_flops` in any way.

### Dynamic Factors *(all default to 0 = disabled)*

- **`reputation_escalation_factor`** — Geometrically multiplies reputation cost per failed audit. A lab caught repeatedly faces an exponentially larger perceived punishment.
- **`racing_gap_sensitivity`** — Labs ahead of the capability mean increase their `racing_factor`; labs behind decrease it. Drives competitive arms-race dynamics.
- **`capability_scale`** — Normalization factor for the racing gap calculation. Tune to control the magnitude of the racing dynamic.

---

## What Actually Drives Compliance

The deterrence condition each lab evaluates every step:

> **Cheat if `gain > p_eff × b_total`**

| Component | Driven By |
|---|---|
| **`gain`** (motive) | `economic_value`, `racing_factor × capability_value`, `market_price` |
| **`p_eff`** (detection risk) | `base_prob`, `high_prob`, `false_negative_rate`, `backcheck_prob`, `whistleblower_prob`, `audit_coefficient`, `flop_threshold` (via signal) |
| **`b_total`** (perceived punishment) | `penalty_amount` / `penalty_fixed` / `penalty_percentage` / `penalty_ceiling`, `collateral_amount`, `reputation_sensitivity`, `risk_profile` |
