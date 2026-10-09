"""Live point-grid soil-moisture model output; never treated as farm measurement."""
from __future__ import annotations

import json
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DISTRICT_COORDINATES = {
    "nashik": {"lat": 19.9975, "lon": 73.7898, "name": "Nashik district reference point"},
    "pune": {"lat": 18.5204, "lon": 73.8567, "name": "Pune district reference point"},
    "nagpur": {"lat": 21.1458, "lon": 79.0882, "name": "Nagpur district reference point"},
    "aurangabad": {"lat": 19.8762, "lon": 75.3433, "name": "Chhatrapati Sambhajinagar reference point"},
    "solapur": {"lat": 17.6599, "lon": 75.9064, "name": "Solapur district reference point"},
}
VARIABLES = {
    "topsoil_volumetric_m3m3": ("soil_moisture_0_to_7cm", "0–7 cm"),
    "root_zone_volumetric_m3m3": ("soil_moisture_7_to_28cm", "7–28 cm"),
    "subsoil_volumetric_m3m3": ("soil_moisture_28_to_100cm", "28–100 cm"),
}
API_URL = "https://api.open-meteo.com/v1/ecmwf"


def _unavailable(district: str, reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "source": "Open-Meteo ECMWF model API", "district": district,
            "observation_type": "modeled_grid_output_not_farm_measurement", "layers": [
                {"name": key, "depth": depth, "value": None, "unit": "m³/m³"}
                for key, (_, depth) in VARIABLES.items()], "trend_history": [], "reason": reason,
            "assessment_use": False}


def get_soil_moisture_telemetry(district: str) -> dict[str, Any]:
    """Fetch current/recent model output for the selected district reference point."""
    location = DISTRICT_COORDINATES.get(district.strip().casefold())
    if not location:
        return _unavailable(district, "No configured reference point for this district. Add an authorized farm location to request a farm-level grid cell.")
    params = {"latitude": location["lat"], "longitude": location["lon"],
              "hourly": ",".join([v[0] for v in VARIABLES.values()] + ["soil_temperature_0_to_7cm"]),
              "past_hours": 24, "forecast_hours": 48, "timezone": "Asia/Kolkata"}
    req = Request(f"{API_URL}?{urlencode(params)}", headers={"Accept": "application/json", "User-Agent": "Sage-telemetry/1.0"})
    try:
        with urlopen(req, timeout=8) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            return _unavailable(location["name"], "Provider response exceeded the configured size limit.")
        data = json.loads(raw)
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        if not times or not all(hourly.get(variable, []) for variable, _ in VARIABLES.values()):
            return _unavailable(location["name"], "The provider returned no soil-moisture values for this location and time window.")
        values = {}
        now_local = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
        parsed_times = [datetime.fromisoformat(str(value)) for value in times]
        eligible = [i for i, value in enumerate(parsed_times) if value <= now_local]
        latest_index = eligible[-1] if eligible else 0
        for key, (variable, _) in VARIABLES.items():
            series = hourly[variable]
            index = latest_index if latest_index < len(series) else None
            if index is None or not isinstance(series[index], (int, float)) or not math.isfinite(series[index]):
                return _unavailable(location["name"], "The provider returned missing soil-moisture values for one or more layers.")
            values[key] = round(float(series[index]), 4)
        observed_at = times[latest_index]
        model_age_hours = max(0.0, (now_local - parsed_times[latest_index]).total_seconds() / 3600)
        histories = []
        for i in range(0, min(latest_index + 1, len(times)), 6):
            histories.append({"time": times[i], **{key: hourly[var][i] for key, (var, _) in VARIABLES.items()
                                                    if i < len(hourly.get(var, []))}})
        forecast_history = []
        future_indices = [i for i, value in enumerate(parsed_times) if value > now_local]
        for i in future_indices[::6]:
            forecast_history.append({"time": times[i], **{key: hourly[var][i] for key, (var, _) in VARIABLES.items()
                                                            if i < len(hourly.get(var, []))}})
        return {"status": "live_model_output", "source": "Open-Meteo ECMWF model output",
                "model": "ECMWF forecast/model endpoint",
                "district": location["name"], "grid_point": {"latitude": data.get("latitude"), "longitude": data.get("longitude")},
                "grid_elevation_m": data.get("elevation"),
                "as_of": observed_at, "valid_time": observed_at, "issue_time": None,
                "freshness_status": "stale" if model_age_hours > 6 else "current",
                "model_age_hours": round(model_age_hours, 1),
                "time_semantics": "latest returned hourly modeled value; provider does not expose issue time in this response",
                "observation_type": "modeled_grid_output_not_farm_measurement",
                "layers": [{"name": key, "depth": depth, "value": values[key], "unit": "m³/m³"}
                           for key, (_, depth) in VARIABLES.items()],
                "soil_temperature_c": (hourly.get("soil_temperature_0_to_7cm") or [None])[latest_index],
                "trend_history": histories, "forecast_history": forecast_history, "assessment_use": False,
                "limitations": ["Grid-model output is not an in-field sensor reading.",
                                "District reference points are approximate; farm coordinates are not currently stored.",
                                "Values are displayed as telemetry only and are not used in assessments."]}
    except Exception as exc:
        # Keep provider/network details out of user output and logs.
        return _unavailable(location["name"], f"Soil model data could not be retrieved ({type(exc).__name__}).")
