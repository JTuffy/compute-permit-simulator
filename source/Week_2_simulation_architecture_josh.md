# Week 2: Simulation Architecture & Parameters
**Owner:** Josh Tuffy
**Date:** January 22, 2026
**Source Document:** AISC2026_CPM_Week2_20260122.pdf

## Overview
This document outlines the initial simulation architecture and component breakdown for the Compute Permit Market simulator. The architecture distinguishes between "High-Lift" core components required for the MVP and "Lower-Lift" features that can be added later.

## Reference Diagram
*   **File:** `JTuffy_V0_Diagram.svg` (Architecture Diagram)

## Component Breakdown

### 1. High-Lift Components (Core / MVP)
These are the most complex and critical parts of the simulation that need to be addressed first.

*   **Actor Behavior:**
    *   **Logic:** Mechanisms for defining how agents (firms/regulators) behave.
    *   **Strategy:** Computation of optimal strategies.
        *   *Potential Approach:* Expected Value calculations.
        *   *Challenge:* High complexity in modeling realistic incentives and decision-making.
*   **Permit Market:**
    *   **Functionality:** A dynamic market mechanism where permits are traded.
    *   **Action Space:** New types of actions available to agents (buy, sell, hold).
    *   **Price Resolution:** Market clearing prices determined at each turn.
    *   **Strategy Dependencies:** Agent strategies will likely depend on historical prices ($t_{-1}$).

### 2. Lower-Lift Components (Extensions)
These features are modular and can be layered onto a working MVP.

*   **Banking:** Allowing firms to save permits for future use.
*   **Price Collars:** Mechanisms to floor or cap permit prices (regulation).
*   **Thresholds:** specific trigger points for regulatory intervention or audit.
*   **Grandfathering:** Allocation of permits based on historical emissions/compute existing capacity.

## Assessment
*   **Feasibility:** A complete simulation represents "substantial work."
*   **Risk:** Core components (Actor Behavior, Market Dynamics) may be computationally or architecturally intractable if not simplified.
