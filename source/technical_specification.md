# Technical Specification: Compute Permit Simulator

## 1. Project Overview

A simulation of an AI Compute Permit Market to model the interaction between AI Labs and a Regulator (Governor). The simulation explores the **Deterrence Model**: under what conditions do rational agents choose compliance?

### 1.1 Project Structure

```text
compute_permit_sim/
├── domain/                # Economic & Enforcement logic (Pure Python)
│   ├── agents.py          # Lab/Firm logic: compute value, compliance check
│   ├── enforcement.py     # Auditor logic: signals, penalties
│   └── market.py          # Trading logic: permit prices, market clearing
├── infrastructure/        # Simulation engine (Mesa integration)
│   ├── model.py           # The global world state and turn-scheduler
│   └── data_collect.py    # Metrics: total welfare, risk violations
├── scenarios/             # JSON configs for scenarios (audit params, market type)
└── main.py                # Entry point
```

## 2. Core Model Specification

### 2.1 Agents (Labs)
Labs are profit-maximizing entities that make a binary decision: **Comply** (buy permit) or **Defect** (train without permit).

**Key Attributes:**
- `gross_value` ($v_i$): Value generated from a training run.
- `risk_profile`: Multiplier on perceived penalty.
- `compliance_decision`: Based on the condition $p_{eff} \cdot B \ge g$.
  - $p_{eff}$: Effective detection probability.
  - $B$: Total effective penalty (Fine + Reputation).
  - $g$: Gain from cheating (Permit Cost + Racing Value).

### 2.2 Governor (Auditor)
The Governor enforces compliance through audits based on noisy signals.

**Signal Model:**
- **False Positive Rate ($\alpha$)**: $P(\text{signal}=1 | \text{compliant})$
- **False Negative Rate ($1-\beta$)**: $P(\text{signal}=0 | \text{non-compliant})$

**Audit Strategy:**
- If Signal=1 (Suspicious): Audit with probability $\pi_1$ (`high_prob`).
- If Signal=0 (Clean): Audit with probability $\pi_0$ (`base_prob`).

**Effective Detection:**
$$ p_{eff} = p_s + (1 - p_s) \cdot p_b $$
Where $p_s$ is the probability of a signal-triggered audit, and $p_b$ is the backcheck probability.

### 2.3 Market
The market determines permit allocation and pricing. Two modes are supported:

1.  **Clearing Market (Cap-and-Trade):**
    - Supply is fixed at $Q$ (`token_cap`).
    - Price is set by the $Q$-th highest bid (marginal pricing).
    - Highest $Q$ bidders receive permits.

2.  **Fixed Price Market (Carbon Tax / Unlimited):**
    - Price is fixed (`fixed_price`).
    - Supply is effectively unlimited.
    - Any agent with $v_i \ge \text{price}$ purchases a permit.

## 3. Simulation Loop (Turn Sequence)

1.  **Trading Phase:**
    - Agents submit bids (willingness to pay).
    - Market resolves price and allocates permits.
    - Agents pay for permits (reducing wealth).

2.  **Compliance Phase:**
    - Agents without permits decide whether to run without one (defect).
    - Agents with permits always comply (run legally).

3.  **Enforcement Phase:**
    - Governor monitors signals for all running agents.
    - Audits are triggered based on signal and policy.
    - Non-compliant agents caught are penalized (fine deducted).

## 4. Key Variables & Parameters

| Component | Variable | Definition | Recommended Value/Range |
|---|---|---|---|
| Deterrence | $P$ | Effective Punishment | 0.2 $\to$ 0.8 |
| Monitoring | $p_{eff}$ | Detection Probability | 0.25 $\to$ 0.75 |
| Market | $p$ | Clearing or Fixed Price | Endogenous or Fixed |
| Auditing | $\pi_1$ | High-suspicion audit probability | $\min(1, \frac{P\beta}{v^*-c})$ |

## 5. Configuration

Scenarios are defined in `scenarios/config.json`. Key configuration sections:

- `audit`: Detection probabilities, signal rates ($\alpha, \beta$), penalties.
- `market`: `token_cap` (quantity) or `fixed_price`.
- `lab`: Ranges for `gross_value` and `risk_profile` to generate heterogeneous agents.