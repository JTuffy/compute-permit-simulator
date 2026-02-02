# Technical Documentation: Compute Permit Simulator

This document describes the functional relationships between components. For usage and installation, see [README.md](README.md).

## System Architecture

(Paste into an editor with Mermaid support if needed)
```mermaid
graph TB
    subgraph "Entry Points"
        CLI[main.py<br/>CLI Runner]
        UI[app.py<br/>Solara Entry]
        HEAT[heatmap.py<br/>Analysis Tool]
    end

    subgraph "Visualization Layer"
        SOLARA[solara_app.py<br/>Dashboard Components]
        STATE[state.py<br/>SimulationManager<br/>Reactive State]
        COMP[components.py<br/>UI Widgets]
    end

    subgraph "Infrastructure Layer"
        MODEL[model.py<br/>ComputePermitModel<br/>Mesa Integration]
        CONFIG[config_manager.py<br/>Scenario I/O]
        DATA[data_collect.py<br/>Metrics Collection]
    end

    subgraph "Domain Layer"
        LAB[agents.py<br/>Lab<br/>Compliance Logic]
        MARKET[market.py<br/>SimpleClearingMarket<br/>Price Discovery]
        AUDITOR[enforcement.py<br/>Auditor<br/>Signal & Audit]
    end

    subgraph "Configuration"
        SCHEMA[schemas.py<br/>Pydantic Models<br/>ScenarioConfig<br/>AuditConfig<br/>MarketConfig<br/>LabConfig]
    end

    CLI --> MODEL
    UI --> SOLARA
    HEAT --> MODEL
    
    SOLARA --> STATE
    SOLARA --> COMP
    STATE --> MODEL
    STATE --> CONFIG
    
    MODEL --> LAB
    MODEL --> MARKET
    MODEL --> AUDITOR
    MODEL --> DATA
    MODEL --> SCHEMA
    
    CONFIG --> SCHEMA
    LAB --> SCHEMA
    MARKET --> SCHEMA
    AUDITOR --> SCHEMA
    
    style MODEL fill:#e1f5ff
    style STATE fill:#fff4e1
    style SCHEMA fill:#e8f5e9
```

## Component Relationships

**Domain Layer** (`domain/`): Model logic.
- `agents.py`: `Lab` class implements compliance decision (`decide_compliance()`) using deterrence condition `p_eff * B_total >= gain`
- `market.py`: `SimpleClearingMarket` handles price discovery (Qth highest bid) and permit allocation
- `enforcement.py`: `Auditor` generates noisy signals and decides audits

**Infrastructure Layer** (`infrastructure/`): Mesa integration and simulation control.
- `model.py`: `ComputePermitModel` the 4-phase simulation loop (see below)
- `config_manager.py`: Loads/saves JSON scenarios as validated `ScenarioConfig` objects
- `data_collect.py`: Reporter functions for Mesa DataCollector (compliance rate, price)

**Visualization Layer** (`vis/`): Interactive UI and state management.
- `state.py`: `SimulationManager` manages reactive state, bridges UI ↔ Model
- `solara_app.py`: Solara components (ConfigPanel, Dashboard, InspectorTab)
- `components.py`: Reusable UI widgets (scatter plots, range controls)

**Configuration** (`schemas.py`): Pydantic models (`AuditConfig`, `MarketConfig`, `LabConfig`, `ScenarioConfig`) used throughout for type-safe configuration.

## Simulation Loop

The `ComputePermitModel.step()` method executes four phases:

(Paste into an editor with Mermaid support if needed)
```mermaid
sequenceDiagram
    participant UI as Solara UI
    participant SM as SimulationManager
    participant Model as ComputePermitModel
    participant Market as SimpleClearingMarket
    participant Lab as Lab Agents
    participant Auditor as Auditor
    participant DC as DataCollector

    UI->>SM: step() or play_loop()
    SM->>Model: step()
    
    Note over Model: Phase 1: Trading
    Model->>Lab: get_bid() for each agent
    Lab-->>Model: bids
    Model->>Market: allocate(bids)
    Market-->>Model: (price, winners)
    Model->>Lab: Update has_permit, deduct wealth
    
    Note over Model: Phase 2: Compliance
    Model->>Auditor: compute_effective_detection()
    Auditor-->>Model: p_eff
    Model->>Lab: decide_compliance(price, penalty, p_eff)
    Lab-->>Model: is_compliant
    
    Note over Model: Phase 3: Enforcement
    Model->>Auditor: generate_signal(is_compliant)
    Auditor-->>Model: signal
    Model->>Auditor: decide_audit(signal)
    Auditor-->>Model: should_audit
    Model->>Lab: Apply penalties if caught
    
    Note over Model: Phase 4: Data Collection
    Model->>DC: collect(model)
    Model->>Model: get_agent_snapshots()
    Model-->>SM: Updated state
    SM->>SM: Update reactive variables
    SM-->>UI: Trigger re-render
```

**Phase 1 - Trading**: Agents submit bids → `Market.allocate()` → price discovery → permit allocation → wealth deduction

**Phase 2 - Compliance**: Calculate `p_eff` → agents without permits call `decide_compliance()` → agents with permits auto-comply

**Phase 3 - Enforcement**: `Auditor.generate_signal()` → `decide_audit()` → apply capacity constraints → execute audits → apply penalties

**Phase 4 - Data Collection**: `DataCollector.collect()` → `get_agent_snapshots()` → update reactive state
