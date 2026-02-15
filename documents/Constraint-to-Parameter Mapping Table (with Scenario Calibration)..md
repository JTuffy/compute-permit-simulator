Constraint-to-Parameter Mapping Table 
(with Scenario Calibration)
Sue CHENG

Here is a summary of the three suggested calibrated scenarios defined for testing the “Governance Trilemma” in the simulator.
1.	Scenario 1: Lawless World (Status Quo)
A fragmented landscape where a lack of standardized metrics and oversight creates a high-evasion environment, making safety compliance a rare and easily bypassed cost for labs.

2.	Crisis World (Maximum Safety)
A rigid "command-and-control" regime that attempts to force near-perfect safety through intrusive telemetry and extreme audit frequencies, creating significant administrative friction for both labs and regulators. 

3.	Maxwell World (Smart Enforcement)
An incentive-aligned "smart enforcement" model that utilizes efficient permit markets and high-impact hardware monitoring to make safety compliance the most economically rational path for innovation.

Regulatory Constraint	Parameter in the Deterrence Model	Scenario 1: Lawless	Scenario 2: Crisis	Scenario 3: Maxwell 	Implication for Model (with Source & Evidence)
1. Limited audit capacity	pa (base audit rate)	0.05

Represents negligent oversight or minimal funding. 	0.3

Represents the state capacity ceiling that regulator investigates nearly 1 in 3 firms.	0.1

Targeted efficiency. High enough to be a credible threat but keeps the administrative burden low for the agency. 	Monitoring is structurally limited by budget and personnel, pa should be low in the model.

To achieve compliance, i.e. maintain p x B ≥ g, regulator should implement higher penalties (B) or collateral (K). 

Source: EU ETS
2. Measurement uncertainty and estimation	𝜖𝐼𝐼 (type-II error)	0.4

High noise environment where violations are easily missed.	0.1

Assumes high-cost telemetry to force near-perfect accuracy. 
	0.4

Accepts real-world noise as a fixed technical constraint. 	Compute measurement inevitably relies on proxies and estimations, as direct observation is not currently feasible.

In the model, this uncertainty is represented by type-II error,  which occurs when an audit is conducted but the regulator fails to catch a violation. Higher error rate (𝜖𝐼𝐼) directly reduces the overall detection probability (p). 

Source: JRC 2025
3. Extreme information asymmetry / reliance on actor self-monitoring and self-reporting	pm (global monitoring)	0

Reliance on self-reports with no external verification.	1.0

Total transparency of all chips and energy at all times.	0.2

Uses hardware/CSP proxy checks which are cheaper than full audits.	FLOPs are unobservable. Similar to Montero’s study on urban pollution, monitoring proxies is more critical than audits. 

Source: Montero (2025)

4. Decentralized Infrastructure	c(i) (firm-specific coefficient)	0.8

High evasion; labs effectively hide 80% of runs via run-splitting.  	0.1

Strict controls to make evasion nearly impossible. 	0.5

Some privacy remains, but hardware traceability limits large-scale evasion. 	AI training is conducted across multiple cloud providers, jurisdictions, and legal entities, allowing developers to restructure training runs to reduce regulatory visibility.

Firms with highly distributed or transnational infrastructure can effectively lower their individual detection probability (p) by making their training runs harder to track than those of a firm using a single, more visible data centre.

Run-splitting allows firms to lower their detection probability. 

Source: Singh, S., et al. (2024)

5. Absence of Standardized Risk Metrics	ΔC (permit cost savings)	$70M

Savings from gaming thresholds to skip permits for frontier runs (assume 1026 FLOPS). 	$70M

The incentive to cheat is identical (i.e. $70M) even though the regulator is strict. *If set to 0, it means there is no financial benefit to skip a permit. 	$2M

Market efficiency lowers the permit cost to a level where compliance becomes the “cheapest” business strategy. This value is calibrated to counteract the Racing Factor (V) . 	Unlike CO₂ emissions in EU ETS, there is no universally accepted unit of AI risk. 

This ambiguity allows firms to exploit "noise" in the metric to report their activity just below the regulatory threshold, i.e. C(reported) = 0, which maximizes their permit cost savings (ΔC) and makes cheating more attractive.  

Source: According to Heim & Koessler (2024), a model trained with 1025 and 1026 FLOPS of compute cost $7M and $70M to train respectively. 
6. Limited Liability	K (Refundable Collateral)	$0

No upfront commitment; labs only pay if caught and solvent. 	$15.75M

Upfront bond secures the penalty. Take ref from EU AI Act fine caps, €15M = $15.75M.

Alternative test case: $0 (follow EU AI Act to have ex-post fines instead of collateral)  	$15.75M

Upfront bond secures the penalty; forfeited upon violation to ensure deterrence. 	Upfront bond used to secure the penalty when ex-post fines are uncollectable.
 
Source: EU AI Act (Regulation 2024/1689) relies on ex-post fines.
 
Article 99(4): “Non-compliance with any of the following provisions…shall be subject to administrative fines of up to 15,000,000 EUR or, if the offender is an undertaking, up to 3% of its total worldwide annual turnover for the preceding financial year, whichever is higher.


