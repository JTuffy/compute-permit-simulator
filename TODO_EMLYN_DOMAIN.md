# Domain TODO

> Owner: Emlyn
> Branch: `domain-logic-mvp`
> Reference documents: `source/`, primarily `source/AISC Week 2 - The Deterrence Model`
> This list tracks all work on `src/compute_permit_sim/domain/`.
> Each item references the source document and section it implements.

---

## Phase 0 - Get a v0.1 MVP working with fixed permit price and unlimited permit supply

- [x] Basic instantiation tests (`tests/test_basics.py`)
- [x] Fixed price market logic (`src/compute_permit_sim/domain/market.py`)
- [x] Integration tests for fixed price scenario (`tests/test_integration.py`)

## Phase 1 — Fix What's Broken (MVP Baseline)

### 1.1 `agents.py` — Store compliance decision

- [x] `decide_compliance()` must write its result to `self.is_compliant` before returning.

### 1.2 `enforcement.py` — Move `p_eff` into Governor

- [x] Add `compute_effective_detection(self) -> float` to the `Governor` class.

### 1.3 `enforcement.py` — Move penalty application into Governor

- [x] Add `apply_penalty(self, is_compliant: bool, has_permit: bool) -> float` to Governor.

### 1.4 `market.py` — Return allocation with price

- [x] Add `allocate(self, bids: list[tuple[int, float]]) -> tuple[float, list[int]]` that returns `(clearing_price, list_of_winning_lab_ids)`.

### 1.5 `agents.py` — Add `get_bid()` method

- [x] Add `get_bid(self, cost: float = 0.0) -> float` returning `max(0.0, self.gross_value - cost)`.

---

## Phase 2 — Implement the Full Deterrence Model

### 2.1 Detection probability decomposition

- [x] **Base audit rate `p_a`.** Already exists as `AuditConfig.base_prob`. No change needed.
- [x] **Firm-specific audit coefficient `c(i)`.** (Implemented in `model.py` dynamics)
- [x] **Type-II error `ε_II`.** (Implemented in `model.py` via `false_negative_rate`)
- [x] **Backcheck probability `p_b`.** (Implemented in `model.py` dynamics)
- [ ] **Other detection factors (future).**

### 2.2 Penalty decomposition

- [x] **Regulatory penalty `B_r`.** Keep as existing `penalty_amount`.
- [ ] **Collateral `B_k`.** [DEFERRED]
- [ ] **Reputation cost `R`.** Add `reputation_sensitivity`. (Field exists, passed to agent, but effect needs specific tests if desired).

### 2.3 Gain for cheating decomposition

- [ ] **Permit cost savings `ΔC`.** `ΔC = C(real) − C(reported)`.
- [ ] **Detection scaling with ΔC.** 
- [x] **Capability value `V = c_r × V_b`.** (Fields exist, passed to agent).
- [x] **Total gain: `g = ΔC + V`.** (Implemented in `agents.py`).

### 2.4 Rewrite `decide_compliance()` to use `p × B ≥ g`

- [x] Refactor the method to express the deterrence condition directly.

---

## Phase 3 — Schema & Config Updates

### 3.1 `schemas.py` updates

- [x] Add to `AuditConfig`: `backcheck_prob`, `type_ii_error` (as FNE).
- [x] Add to `LabConfig`: `audit_coefficient`, `reputation_sensitivity`, `capability_value`, `racing_factor` ranges.

### 3.2 `scenarios/config.json` updates

- [ ] Extend each scenario with new fields.
- [ ] Add Scenario 4: "Collateral Enforcement".

---

## Phase 4 — Tests for Domain Logic

### 4.1 Core deterrence tests (`tests/test_agents.py` / `tests/test_dynamics.py`)

- [x] **T1: `p × B ≥ g` → comply.** (Covered by `test_higher_audit_rate_higher_compliance`)
- [x] **T2: `p × B < g` → cheat.** (Covered by `test_higher_audit_rate_higher_compliance` low case)
- [x] **T3: Has permit → always comply.** (Implicit in model logic, verified by integration tests).
- [x] **T4: Both options unprofitable → don't run (comply).**
- [x] **T5: Compliance monotonic in P.** (Implicit in dynamics tests).
- [x] **T6: Compliance monotonic in p.** (`test_higher_audit_rate_higher_compliance`)
- [ ] **T7: Higher `risk_profile` → comply at lower threshold.**
- [ ] **T8: Firms below threshold always comply.** 
- [x] **T9: Racing factor increases non-compliance.** (`test_high_racing_factor_zero_compliance`)

### 4.2 Enforcement tests (`tests/test_enforcement.py` / `tests/test_dynamics.py`)

- [x] **T10: `p_eff` formula correct.** 
- [x] **T11: With backcheck, `p_eff` increases.** (`test_higher_backcheck_rate_higher_compliance`)
- [ ] **T12: Signal FPR/TPR statistical test.**
- [ ] **T13: Audit rates statistical test.**
- [x] **T14: Penalty application.** (Implicit in integration tests).
- [ ] **T15: Collateral refund.** [DEFERRED]

### 4.3 Market tests (`tests/test_market.py`)

- [x] **T16-T21: Market logic tests.**
