from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Overrides(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    rainfall_change_pct: float = Field(default=0, ge=-100, le=100)
    heatwave_days: int = Field(default=0, ge=0, le=45)
    heatwave_growth_stage: Literal["planting", "vegetative", "flowering", "grain_fill", "harvest"] = "flowering"
    market_price_change_pct: float = Field(default=0, ge=-90, le=100)
    irrigation_fraction: float | None = Field(default=None, ge=0, le=1)
    assumed_informal_bridge_inr: float = Field(default=0, ge=0, le=1000000)


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    borrower_id: str = "B-DEMO-001"
    as_of: date = date(2026, 10, 9)
    overrides: Overrides = Field(default_factory=Overrides)
    action_id: Literal["reschedule_30d", "split_payment", "none"] = "none"


class ScenarioBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    borrower_id: str
    scenario_id: str
    input_hash: str
    comparison_context_hash: str
    engine_version: str
    assessment_as_of: date
    source_versions: dict[str, str]
    source_snapshot_ids: list[str]
    frozen_context: dict[str, Any]
    scenario_request: dict[str, Any]
    claim_scope: Literal["synthetic_lending_scenario_conditional"]
    baseline: dict[str, Any]
    stress: dict[str, Any]
    stress_with_action: dict[str, Any] | None
    action_status: Literal["not_selected", "simulated_proposal", "ineligible"]
    action_candidates: list[dict[str, Any]]
    comparison_deltas: dict[str, Any]
    repayment_bridge: dict[str, Any]
    debt_cycle: list[dict[str, Any]]
    debt_warnings: list[dict[str, Any]]
    input_data_status: dict[str, list[str]]
    risk_semantics: str
    drivers: list[str]
    warnings: list[str]
