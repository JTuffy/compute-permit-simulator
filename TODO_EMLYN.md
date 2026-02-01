# Todo: Model Alignment & Scenarios

Refined based on user feedback.

## 1. Model Alignments

### A. Compute Permit Threshold (High Priority)
**Goal**: Permits only required if `run_size > threshold`.
**Proposal**:
*   Add `last_run_size: float` to `Lab` (units: e.g., ZettaFLOPs).
    *   *Why*: Decouples "Value" ($V$) from "Compute Cost" ($C$). High value small models shouldn't trigger regulation.
*   Add `permit_threshold: float` to `Market` / `Auditor`.
*   **Logic**: Cheat = `last_run_size >= permit_threshold` AND `!has_permit`.

### B. Dynamic Reputation Damage
**Goal**: Failed audits increase future compliance pressure.
**Proposal**:
*   If Audit Catch: `lab.reputation_sensitivity += stigma_increment` (or `*= multiplier`).
*   Result: Repeat offenders face effectively higher $B$, forcing compliance or exit.

### C. Racing Factor Decay
**Goal**: Urgency fades over time.
**Proposal**: Decay `racing_factor` each round ($c_r(t+1) = c_r(t) \cdot \gamma$).

### D. Dynamic Detection ($p(\Delta C)$)
**Goal**: Big cheats are harder to hide.
**Proposal**: $p_{eff}$ scales with usage gap ($\Delta C = \text{Actual} - \text{Reported}$).

### E. Collateral (Low Priority)
**Proposal**: Add `collateral_posted` to penalty breakdown.

### F. Telemetry & Backchecks (New)
**Goal**: Analyze "Safe Harbors" (Audit Failure vs Backcheck Catch).
**Proposal**:
*   `Auditor` returns `AuditResult(triggered, source, caught, penalty)`.
*   Sources: `signal` (primary), `backcheck` (secondary).
*   Log results to track distinct catch vectors.

## 2. Scenarios

### A. Compliance Transition ($p \times B \ge g$)
*   **Sweep**: Detection Prob ($p$) vs Fixed Gain ($g$).
*   **Metric**: Compliance Rate (Line Plot).

### B. High Stakes Heatmap
*   **Sweep**: Racing Factor ($c_r$) vs Detection Prob ($p$).
*   **Metric**: Compliance (Heatmap). Shows urgency overriding enforcement.

### C. Backcheck Safety Analysis
*   **Sweep**: Backcheck Prob vs False Negative Rate.
*   **Metric**: Caught Count by Source (Stacked Bar).

### D. Reputation Cascade
*   **Sim**: Long-running with Dynamic Reputation.
*   **Metric**: Cheater Count (Time Series). Expect drop as $R \uparrow$.
