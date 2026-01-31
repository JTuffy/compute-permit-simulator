"""State management for the visualization infrastructure."""

import asyncio
import json
import time
from pathlib import Path

import pandas as pd
import solara
import solara.lab

from compute_permit_sim.infrastructure.model import ComputePermitModel
from compute_permit_sim.schemas import (
    AuditConfig,
    LabConfig,
    MarketConfig,
    ScenarioConfig,
    SimulationRun,
    StepResult,
)


class SimulationManager:
    """Manages the simulation state and logic, decoupled from the View."""

    def __init__(self):
        # --- Full Configuration State ---
        # Lab Config
        self.n_agents = solara.reactive(20)
        self.gross_value_min = solara.reactive(0.5)
        self.gross_value_max = solara.reactive(1.5)
        self.risk_profile_min = solara.reactive(0.8)
        self.risk_profile_max = solara.reactive(1.2)

        # Market Config
        self.token_cap = solara.reactive(5)

        # Audit/Governor Config
        self.base_prob = solara.reactive(0.1)
        self.high_prob = solara.reactive(0.1)  # Default equal for simple start
        self.signal_fpr = solara.reactive(0.1)
        self.signal_tpr = solara.reactive(0.9)
        self.penalty = solara.reactive(0.5)
        self.audit_budget = solara.reactive(5)

        # Sim Config
        self.steps = solara.reactive(50)

        # --- Model State ---
        self.model = solara.reactive(None)
        self.step_count = solara.reactive(0)
        self.compliance_history = solara.reactive([])
        self.price_history = solara.reactive([])
        self.agents_df = solara.reactive(None)  # Current step agent snapshot
        self.is_playing = solara.reactive(False)

        # --- Run History State ---
        self.current_run_steps: list[StepResult] = []
        self.run_history = solara.reactive([])  # List[SimulationRun]
        self.selected_run = solara.reactive(None)  # SimulationRun | None

        # --- Scenario State ---
        self.scenarios = solara.reactive({})
        self.selected_scenario = solara.reactive("Custom")

        # Load scenarios immediately
        self._load_scenarios()

    def _load_scenarios(self):
        path = Path("scenarios/config.json")
        if path.exists():
            with open(path, "r") as f:
                self.scenarios.value = json.load(f)

    def apply_scenario(self, name):
        """Load parameters from a named scenario."""
        if name in self.scenarios.value:
            c = self.scenarios.value[name]

            # Apply Top Level
            self.n_agents.value = c.get("n_agents", 20)
            self.token_cap.value = c.get("token_cap", 5)
            self.steps.value = c.get("steps", 50)

            # Audit
            self.base_prob.value = c.get("base_audit_prob", 0.1)
            self.high_prob.value = c.get("high_audit_prob", self.base_prob.value)
            self.signal_fpr.value = c.get("signal_fpr", 0.1)
            self.signal_tpr.value = c.get("signal_tpr", 0.9)
            self.penalty.value = c.get("penalty", 0.5)
            self.audit_budget.value = c.get("audit_budget", 5)

            self.selected_scenario.value = name
            self.reset_model()

    def get_current_config(self) -> ScenarioConfig:
        """Construct a Pydantic config from current reactive state."""
        return ScenarioConfig(
            name=self.selected_scenario.value,
            n_agents=self.n_agents.value,
            steps=self.steps.value,
            audit=AuditConfig(
                base_prob=self.base_prob.value,
                high_prob=self.high_prob.value,
                signal_fpr=self.signal_fpr.value,
                signal_tpr=self.signal_tpr.value,
                penalty_amount=self.penalty.value,
                audit_budget=int(self.audit_budget.value),
            ),
            market=MarketConfig(token_cap=float(self.token_cap.value)),
            lab=LabConfig(
                gross_value_min=self.gross_value_min.value,
                gross_value_max=self.gross_value_max.value,
                risk_profile_min=self.risk_profile_min.value,
                risk_profile_max=self.risk_profile_max.value,
            ),
            seed=None,
        )

    def reset_model(self):
        """Initialize or reset the Mesa model."""
        config = self.get_current_config()

        self.model.value = ComputePermitModel(config)
        self.step_count.value = 0
        self.compliance_history.value = []
        self.price_history.value = []
        self.agents_df.value = None
        self.is_playing.value = False
        self.current_run_steps = []  # Clear step history
        self.selected_run.value = None  # Clear detailed view selection to show live

    def step(self):
        """Advance the simulation one step."""
        if self.model.value is None:
            self.reset_model()

        self.model.value.step()
        self.step_count.value += 1

        # Update plotting data
        df = self.model.value.datacollector.get_model_vars_dataframe()
        if not df.empty:
            self.compliance_history.value = df["Compliance_Rate"].tolist()
            self.price_history.value = df["Price"].tolist()

        # Capture Granular Agent State
        # We also want to capture "Phase" info if possible, but Mesa step is atomic.
        # For now, we capture the post-step state.
        agents_data = []
        for a in self.model.value.agents:
            if hasattr(a, "domain_agent"):  # Filter for Labs
                d = a.domain_agent

                # Logic to determine if "audited". Not stored on agent persistently?
                # We might need to look at Governor state. For now, basic state.

                agents_data.append(
                    {
                        "ID": d.lab_id,
                        "Value": round(d.gross_value, 2),
                        "Net_Value": round(
                            d.gross_value
                            - (
                                self.model.value.market.current_price
                                if d.has_permit
                                else 0
                            ),
                            2,
                        ),
                        "Compliant": d.is_compliant,
                        "Permit": d.has_permit,
                        "Wealth": round(a.wealth, 2),
                    }
                )
        self.agents_df.value = pd.DataFrame(agents_data)

        # --- Capture StepResult ---
        m = self.model.value
        step_res = StepResult(
            step_id=self.step_count.value,
            market={"price": m.market.current_price, "supply": m.market.max_supply},
            agents=agents_data,
            audit=[],  # Would need to capture from Governor/Model events if available
        )
        self.current_run_steps.append(step_res)

    async def play_loop(self):
        """Async loop for continuous play."""
        while self.is_playing.value:
            # Auto-stop if we exceed configured steps
            if (
                self.model.value
                and self.step_count.value >= self.model.value.config.steps
            ):
                self.is_playing.value = False
                self.pack_current_run()  # Auto-pack on finish
                break

            self.step()
            await asyncio.sleep(0.1)

    def pack_current_run(self):
        """Finalize the current run and add to history."""
        if not self.model.value:
            return

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        run_id = f"{timestamp}_{self.selected_scenario.value}"

        run = SimulationRun(
            id=run_id,
            config=self.get_current_config(),
            steps=self.current_run_steps,
            metrics={
                "final_compliance": self.compliance_history.value[-1]
                if self.compliance_history.value
                else 0,
                "final_price": self.price_history.value[-1]
                if self.price_history.value
                else 0,
            },
        )

        # Add to history (reactive update)
        current_history = list(self.run_history.value)
        current_history.insert(0, run)  # Newest first
        self.run_history.value = current_history
        self.selected_run.value = run  # Auto-select? Maybe.

    def restore_config(self, run: SimulationRun):
        """Restore configuration from a past run."""
        c = run.config

        # Apply Top Level
        self.n_agents.value = c.n_agents
        self.steps.value = c.steps

        # Market
        self.token_cap.value = int(c.market.token_cap)

        # Audit
        self.base_prob.value = c.audit.base_prob
        self.high_prob.value = c.audit.high_prob
        self.signal_fpr.value = c.audit.signal_fpr
        self.signal_tpr.value = c.audit.signal_tpr
        self.penalty.value = c.audit.penalty_amount
        self.audit_budget.value = c.audit.audit_budget

        # Lab
        self.gross_value_min.value = c.lab.gross_value_min
        self.gross_value_max.value = c.lab.gross_value_max
        self.risk_profile_min.value = c.lab.risk_profile_min
        self.risk_profile_max.value = c.lab.risk_profile_max

        # Ideally, we switch the "Scenario Selector" to specific "Restored" or "Custom"
        # so it doesn't look like it belongs to the previous scenario.
        self.selected_scenario.value = "Restored"

        # Reset model to apply these changes immediately (optional, or let user click reset)
        # But if we are in "History View" mode, restoring config shouldn't auto-run.
        # It should just set the values.
        # But we DO want to exit history view maybe?
        # User said: "then takes us to more details... there is a butotn to load the paras for that one to the active params."
        # Does not imply auto-switch. We'll let the UI handle the switch back to live if desired.

    def save_run(self, name_prefix="run"):
        """Persist structured run."""
        if not self.model.value:
            return None

        # Ensure we have a packed run if not already selected
        run_to_save = self.selected_run.value
        if not run_to_save:
            # Create one on the fly from current
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            run_to_save = SimulationRun(
                id=f"{timestamp}_current",
                config=self.get_current_config(),
                steps=self.current_run_steps,
                metrics={},
            )

        run_dir = Path("runs") / run_to_save.id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save structured JSON
        with open(run_dir / "full_run.json", "w") as f:
            f.write(run_to_save.model_dump_json(indent=2))

        return str(run_dir)


# Singleton
manager = SimulationManager()
