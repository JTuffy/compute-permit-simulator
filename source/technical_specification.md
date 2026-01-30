compute_permit_sim/
├── domain/                # Economic & Enforcement logic (Pure Python)
│   ├── agents.py          # Lab/Firm logic: compute value, compliance check
│   ├── enforcement.py     # Auditor logic: signals, penalties, collateral
│   └── market.py          # Trading logic: permit prices, market clearing
├── infrastructure/        # Simulation engine (Mesa/AgentPy integration)
│   ├── model.py           # The global world state and turn-scheduler
│   └── data_collect.py    # Metrics: total welfare, risk violations
├── scenarios/             # YAML/JSON configs for Scenarios 1, 2, and 3
└── main.py                # Entry point for the Apart sprint
2. Core Model Specifications
Agent: Lab (Firm)
The primary decision-maker. Labs are heterogeneous in their Gross Value (v 
i
​
 ) and Risk Profile.

Decision Rule: Choose usage q 
i
​
 ∈{0,1}.

Compliance Logic: If unpermitted, run if v 
i
​
 −c>E[Penalty].

Expected Penalty: P⋅[βπ 
1
​
 +(1−β)π 
0
​
 ].

Agent: Governor (Regulator)
The entity enforcing the Aggregate Cap (Q).

Enforcement Policy: Sets the effective penalty P and audit probabilities π 
1
​
  (high-suspicion) and π 
0
​
  (low-suspicion).

Signal Monitoring: Observes noisy signals s 
i
​
 ∈{0,1} with False Positive Rate α and True Positive Rate β.

3. Key Variables & Parameters
Ground the simulator in the following "source of truth" variables from recent work:

Component	Variable	Definition	Recommended Value/Range
Deterrence	P	Effective Punishment (Collateral K + Fine ϕ)	0.2→0.8
Monitoring	p	Detection Probability (p 
eff
​
 =p 
s
​
 +(1−p 
s
​
 )p 
b
​
 )	0.25→0.75
Market	p	Market-clearing price (p=v 
∗
 −c)	Endogenous
Auditing	π 
1
∗
​
 	Optimal high-suspicion audit probability	min{1, 
Pβ
v 
∗
 −c
​
 }

Export to Sheets

4. Implementation Spec for AI Agents
To ensure an AI agent can build this effectively during the Apart Sprint, use this focused instruction set:

Strict Rule Separation: Do not mix market-clearing logic with agent decision logic. Use a Central Exchange class to resolve permit prices after agents submit their initial demand.

Turn Sequence: (1) Market Price Discovery → (2) Permit Allocation → (3) Labs decide to Run (Compliance Choice) → (4) Signals Realize → (5) Governor Audits → (6) Penalties/Refunds processed.

Visualization: Prioritize a Deterrence Heatmap. Show P on the X-axis, p on the Y-axis, and color-code by Compliance Rate to find the "behavior flip" point.

Recommended Package: PyMarket + Mesa
Using PyMarket for the "high-lift" market clearing and Mesa for the agent interactions will save significant development time during the 3-day sprint.

Would you like me to write the domain/enforcement.py module to handle the signal-contingent audit logic now?

Simulating Markets with Python This video is relevant because it introduces PyMarket, a Python library specifically designed to simplify the design and simulation of various market mechanisms, which directly supports the project's goal of modeling permit trading.

The "Pro" Architecture
We aren't just writing one giant script. We are separating the Economic Logic (the rules of the game) from the Simulation Engine (the clock that runs the game).
+1

The Theory Brain (Domain): This is where all the math lives. It calculates things like whether a lab thinks it’s "worth it" to cheat based on the current penalty and the chance of getting caught.
+4

The Simulation Engine (Infrastructure): This is the manager. It handles the passage of time (the "turns"), collects data on who is winning, and manages the visual output for the research team.
+1

The Scenario Vault: We keep our experiment settings separate. This allows us to quickly switch from a "no-enforcement" world to a "targeted-audit" world without rewriting any code.
+2

The Key Players (Models)
We define the world through three main roles:


The Lab (The Actor): Each lab has its own "personality"—some get more value from compute than others. They are constantly weighing the cost of a legal permit against the risk of an unauthorized training run.
+4


The Governor (The Regulator): This player is trying to keep total compute under a specific limit. They don't have perfect vision, so they rely on suspicious "signals" (like sudden spikes in electricity use) to decide who to audit.
+4

The Market: This is the meeting ground. It’s where permits are traded, and the price of a permit is naturally set by how badly everyone wants to use compute that month.
+2

The "Game Loop" Sequence
Every "month" in the simulation follows a strict order to ensure the results are scientifically valid:


Phase 1: Trading: Labs buy and sell permits based on their needs.


Phase 2: The Choice: Labs decide if they will stick to their permits or "overclock" and hope they don't get caught.


Phase 3: The Signal: The Governor sees "blips" on the radar for everyone, some of which are true violations and some of which are just noise.
+2


Phase 4: Enforcement: The Governor picks labs to audit, seizes collateral from violators, and refunds the "clean" labs.
+2

This structure ensures that the simulation isn't just a toy, but a rigorous tool for testing AI governance policies before they are tried in the real world.
+1

Would you like me to walk through the "Optimal Audit" logic for Scenario 3 to see how the Governor decides who to pick?