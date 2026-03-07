"""
Scratch script: run the 3 canonical scenarios and print all Section 4 metrics.

Net payoff per lab per step:
  = economic_value  (if ran)
  - clearing_price * permits_allocated  (permit cost)
  - penalty  (if caught)
  - collateral_amount  (if seized)

Run from repo root: uv run python analyze_scenarios.py
"""

from compute_permit_sim.services.config_manager import load_scenario
from compute_permit_sim.services.mesa_model import ComputePermitModel, MesaLab

SCENARIO_FILES = [
    "basic/scenario_1_minimal.json",
    "basic/scenario_2_strict.json",
    "basic/scenario_3_smart.json",
]


def run_and_analyze(filename: str) -> None:
    config = load_scenario(filename)
    print(f"\n{'=' * 70}")
    print(f"SCENARIO: {config.name}")
    print(f"  Steps={config.steps}, N={config.n_agents}")
    print(f"  audit.base_prob={config.audit.base_prob}")
    print(f"  audit.false_negative_rate={config.audit.false_negative_rate}")
    print(f"  audit.monitoring_prob={config.audit.monitoring_prob}")
    print(f"  audit.penalty_amount={config.audit.penalty_amount}")
    print(f"  audit.signal_dependent={config.audit.signal_dependent}")
    print(f"  collateral_amount={config.collateral_amount}")
    print(f"  market.fixed_price={config.market.fixed_price}")
    print(f"  market.permit_cap={config.market.permit_cap}")
    print(f"{'=' * 70}")

    model = ComputePermitModel(config=config)

    step_compliance: list[float] = []
    step_prices: list[float] = []
    all_step_payoffs: list[float] = []

    # Audit burden tracking
    total_audits = 0
    audits_on_compliant = 0
    audits_on_violators = 0
    violations_caught = 0

    for step_num in range(1, config.steps + 1):
        model.step()

        mesa_labs = [a for a in model.agents if isinstance(a, MesaLab)]
        clearing_price = model.market.current_price

        compliant_count = sum(1 for a in mesa_labs if a.domain_agent.is_compliant)
        compliance_rate = compliant_count / len(mesa_labs) if mesa_labs else 0.0
        step_compliance.append(compliance_rate)
        step_prices.append(clearing_price)

        for mesa_lab in mesa_labs:
            d = mesa_lab.domain_agent
            ao = mesa_lab.last_audit_status

            ran: bool = ao["ran"]
            penalty: float = ao["penalty"]
            collateral_seized: bool = ao.get("collateral_seized", False)
            permits_allocated = d.permits_held

            gross = d.economic_value if ran else 0.0
            permit_cost = clearing_price * permits_allocated
            collateral_cost = config.collateral_amount if collateral_seized else 0.0
            net = gross - permit_cost - penalty - collateral_cost
            all_step_payoffs.append(net)

            # Audit stats — is_compliant is set by the game loop
            if ao["audited"]:
                total_audits += 1
                if d.is_compliant:
                    audits_on_compliant += 1
                else:
                    audits_on_violators += 1
                    if ao["caught"]:
                        violations_caught += 1

    avg_compliance = sum(step_compliance) / len(step_compliance)
    final_compliance = step_compliance[-1]
    avg_price = sum(step_prices) / len(step_prices)
    final_price = step_prices[-1]
    avg_net_payoff = sum(all_step_payoffs) / len(all_step_payoffs)

    print("\nRESULTS SUMMARY")
    print(f"  Avg compliance (all steps):  {avg_compliance:.1%}")
    print(f"  Final compliance (step {config.steps}): {final_compliance:.1%}")
    print(f"  Avg market price:            ${avg_price:.2f}M")
    print(f"  Final market price:          ${final_price:.2f}M")
    print(f"  Avg net payoff per lab/step: ${avg_net_payoff:.2f}M")
    print(f"\nAUDIT BURDEN (over all {config.steps} steps x {config.n_agents} labs)")
    total_possible = config.steps * config.n_agents
    print(f"  Total lab-steps:             {total_possible}")
    print(
        f"  Total audits fired:          {total_audits}  ({total_audits / total_possible:.1%} of lab-steps)"
    )
    print(
        f"  Audits on compliant firms:   {audits_on_compliant}  ({audits_on_compliant / max(1, total_audits):.1%} of all audits)"
    )
    print(f"  Audits on violators:         {audits_on_violators}")
    print(f"  Violations caught:           {violations_caught}")
    if audits_on_violators > 0:
        print(
            f"  Detection rate:              {violations_caught / audits_on_violators:.1%}"
        )

    print("\nPER-STEP COMPLIANCE:")
    for i, c in enumerate(step_compliance, 1):
        print(f"  Step {i:2d}: {c:.0%}  price=${step_prices[i - 1]:.2f}M")


def main() -> None:
    for f in SCENARIO_FILES:
        try:
            run_and_analyze(f)
        except Exception as e:
            print(f"\nERROR running {f}: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
