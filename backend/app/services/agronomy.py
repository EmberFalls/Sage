"""Date-aligned, explicitly illustrative crop-stage feature construction."""
from datetime import date, timedelta

RULE_VERSION = "illustrative-stage-response-v3"
STAGE_WINDOWS = {"planting": (0, 24), "vegetative": (25, 54), "flowering": (55, 75),
                 "grain_fill": (76, 112), "harvest": (113, 145)}
SENSITIVITY = {
    "Wheat": {"planting": "0.4", "vegetative": "0.6", "flowering": "1", "grain_fill": "0.85", "harvest": "0.25"},
    "Maize": {"planting": "0.45", "vegetative": "0.65", "flowering": "1", "grain_fill": "0.8", "harvest": "0.3"},
}


def stage_calendar(crop: str, sowing_date: date, harvest_date: date) -> list[dict]:
    if crop not in SENSITIVITY:
        raise ValueError(f"No stage-response configuration for {crop}")
    rows = []
    for name, (start_day, end_day) in STAGE_WINDOWS.items():
        start = sowing_date + timedelta(days=start_day)
        active = start <= harvest_date
        end = min(sowing_date + timedelta(days=end_day), harvest_date) if active else start - timedelta(days=1)
        rows.append({"name": name, "start_date": start.isoformat(), "end_date": end.isoformat(),
                     "start_day_after_sowing": start_day, "end_day_after_sowing": end_day,
                     "sensitivity": SENSITIVITY[crop][name],
                     "calendar_status": "assumed_illustrative" if active else "outside_declared_season",
                     "rule_version": RULE_VERSION})
    return rows


def align_heat_event(crop: str, stages: list[dict], start: date, duration_days: int,
                     rainfall_change_pct: float, irrigation_fraction: float) -> dict:
    """Intersect a dated event with stage windows; out-of-season days add no crop-stage stress."""
    end = start + timedelta(days=max(0, duration_days - 1))
    features = {}
    exposed_days = 0
    weighted_days = 0.0
    aligned_stages = []
    stage_overlap_days = {}
    for stage in stages:
        stage_start, stage_end = date.fromisoformat(stage["start_date"]), date.fromisoformat(stage["end_date"])
        active = stage["calendar_status"] != "outside_declared_season"
        overlap = max(0, (min(end, stage_end) - max(start, stage_start)).days + 1) if duration_days and active else 0
        sensitivity = float(stage["sensitivity"])
        exposed_days += overlap
        weighted_days += overlap * sensitivity
        stage_overlap_days[stage["name"]] = overlap
        if overlap:
            aligned_stages.append(stage["name"])
        rain_component = max(0.0, -rainfall_change_pct) / 100 * (1 - irrigation_fraction) * 0.25 if active else 0.0
        heat_component = min(1.0, overlap / 20 * sensitivity)
        features[stage["name"]] = round(min(1.0, heat_component + rain_component), 4)
    return {"start_date": start.isoformat(), "end_date": end.isoformat() if duration_days else None,
            "duration_days": duration_days, "days_inside_crop_calendar": exposed_days,
            "aligned_stages": aligned_stages, "stage_overlap_days": stage_overlap_days,
            "weighted_exposure_days": round(weighted_days, 4), "stage_stress": features,
            "calendar_status": "assumed_illustrative", "weather_status": "hypothetical_scenario"}
