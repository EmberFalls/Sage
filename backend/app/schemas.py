from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    loan_principal_override_inr: Decimal | None = Field(default=None, gt=0, le=Decimal("100000000"))
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
    snapshot_freshness: Literal["current", "stale"] | None = None
    snapshot_stale_reasons: list[str] = Field(default_factory=list)


class BorrowerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    alias: str = Field(min_length=2, max_length=100)
    district: str = Field(min_length=2, max_length=100)
    branch: str = Field(min_length=2, max_length=100)
    crop: Literal["Wheat", "Maize"]
    area_ha: Decimal = Field(gt=0, le=1000)
    irrigation_fraction: Decimal = Field(ge=0, le=1)
    sowing_date: date
    harvest_date: date
    loan_principal_inr: Decimal = Field(gt=0, le=Decimal("100000000"))
    annual_rate: Decimal = Field(ge=0, le=1)
    disbursed_at: date
    due_at: date
    initial_cash_inr: Decimal = Field(ge=0, le=Decimal("100000000"))
    input_cost_inr: Decimal = Field(ge=0, le=Decimal("100000000"))
    living_cost_inr: Decimal = Field(ge=0, le=Decimal("100000000"))
    yield_t_per_ha: Decimal = Field(gt=0, le=100)
    price_inr_per_quintal: Decimal = Field(gt=0, le=Decimal("10000000"))
    sale_fraction: Decimal = Field(gt=0, le=1)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.sowing_date > self.harvest_date:
            raise ValueError("Sowing date must be on or before harvest date")
        if self.disbursed_at > self.due_at:
            raise ValueError("Disbursement date must be on or before due date")
        return self


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    borrower_id: str = Field(min_length=1, max_length=100)
    requested_amount_inr: Decimal = Field(gt=0, le=Decimal("100000000"))
    purpose: str = Field(min_length=3, max_length=500)
    notes: str = Field(default="", max_length=2000)


class ApplicationStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["assessed", "referred_to_officer", "under_review", "reviewed", "approved_in_demo", "rejected_in_demo"]
    rationale: str = Field(min_length=3, max_length=1000)


class LedgerEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    date: date
    kind: Literal["repayment", "fee", "adjustment"]
    amount_inr: Decimal = Field(gt=0, le=Decimal("100000000"))
    note: str = Field(default="", max_length=500)
    event_id: str | None = Field(default=None, min_length=8, max_length=100)


class FeatureSnapshotImport(BaseModel):
    """Governed intake for normalized exports; imported observations never score automatically."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    source_id: Literal["cybench", "agmarknet", "satellite", "soil", "crop_calendar"]
    source_url: str = Field(min_length=8, max_length=500)
    attribution: str = Field(min_length=2, max_length=300)
    license: str = Field(min_length=3, max_length=300)
    dataset_version: str = Field(min_length=1, max_length=100)
    geography: str = Field(min_length=2, max_length=200)
    source_file_hashes: dict[str, str] = Field(default_factory=dict, max_length=20)
    observations: list[dict[str, Any]] = Field(min_length=1, max_length=20000)
