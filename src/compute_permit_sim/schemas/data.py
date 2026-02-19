"""Data Collection and Run Snapshot Schemas."""

from pydantic import BaseModel, ConfigDict, Field

from .config import ScenarioConfig


class AgentSnapshot(BaseModel):
    """Standardized snapshot of a single agent's state at one step."""

    id: int = Field(..., description="Unique agent identifier")
    capacity: float = Field(..., description="Max compute capacity")
    has_permit: bool = Field(..., description="Whether the agent holds a permit")
    used_compute: float = Field(..., description="Actual compute units consumed")
    reported_compute: float = Field(
        ..., description="Compute usage reported to regulator"
    )
    is_compliant: bool = Field(..., description="Compliance status")
    was_audited: bool = Field(..., description="Audit status this step")
    was_caught: bool = Field(..., description="Caught cheating this step")
    penalty_amount: float = Field(..., description="Penalty applied this step")
    revenue: float = Field(..., description="Gross economic value generated")
    economic_value: float = Field(..., description="Agent's base economic value (v_i)")
    risk_profile: float = Field(..., description="Agent's risk profile")
    step_profit: float = Field(..., description="Net profit/loss this step")
    wealth: float = Field(..., description="Cumulative wealth")

    model_config = ConfigDict(frozen=True)


class MarketSnapshot(BaseModel):
    """Snapshot of market state."""

    price: float = Field(..., description="Current clearing price")
    supply: float = Field(..., description="Available permit supply")

    model_config = ConfigDict(frozen=True)


class StepResult(BaseModel):
    """Snapshot of a single simulation step."""

    step: int
    market: MarketSnapshot = Field(
        ..., description="Market state (price, volume, supply)"
    )
    agents: list[AgentSnapshot] = Field(..., description="List of all agent states")
    audit: list[dict] = Field(
        default_factory=list, description="Audit events this step"
    )

    model_config = ConfigDict(frozen=True)


class RunMetrics(BaseModel):
    """Aggregate metrics for a full simulation run."""

    final_compliance: float = Field(..., description="Final compliance rate (0-1)")
    final_price: float = Field(..., description="Final market price")
    total_enforcement_cost: float = Field(..., description="Total cost of audits")
    deterrence_success_rate: float = Field(
        ..., description="Rate of successful deterrence (proxy: compliance)"
    )

    model_config = ConfigDict(frozen=True)


class SimulationRun(BaseModel):
    """Encapsulation of a full simulation run."""

    id: str = Field(..., description="Unique run identifier (timestamp/uuid)")
    sim_id: str | None = Field(None, description="Config Hash ID (short SHA-256)")
    url_id: str | None = Field(
        None, description="Base64-encoded config for shareable URL (?id=...)"
    )
    config: ScenarioConfig
    steps: list[StepResult] = Field(default_factory=list)
    metrics: RunMetrics = Field(..., description="Aggregate metrics")

    model_config = ConfigDict(frozen=True)
