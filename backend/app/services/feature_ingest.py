"""Validate and freeze provider-normalized feature rows without admitting them to scoring."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import uuid4

from app.db import save_source_snapshot

REQUIRED_BY_SOURCE = {
    "cybench": {"yield_t_per_ha", "rainfall_mm", "tmax_c", "tmin_c"},
    "agmarknet": {"market_price_inr_per_quintal"},
    "satellite": {"ndvi"},
    "soil": {"soil_moisture"},
    "crop_calendar": {"crop_calendar_start_doy", "crop_calendar_end_doy"},
}
SOURCE_NAMES = {"cybench": "CY-Bench", "agmarknet": "AGMARKNET", "satellite": "Satellite / NDVI", "soil": "Soil moisture", "crop_calendar": "Crop calendar"}
ALLOWED_UNITS = {
    "yield_t_per_ha": {"t/ha"}, "rainfall_mm": {"mm"}, "tmax_c": {"degC", "°C"}, "tmin_c": {"degC", "°C"},
    "market_price_inr_per_quintal": {"INR/quintal"}, "ndvi": {"1"},
    "soil_moisture": {"m3/m3", "mm"},
    "crop_calendar_start_doy": {"day_of_year"}, "crop_calendar_end_doy": {"day_of_year"},
}


def freeze_feature_import(request) -> dict:
    parsed_url = urlsplit(request.source_url)
    if parsed_url.scheme != "https" or not parsed_url.hostname or parsed_url.username or parsed_url.password:
        raise ValueError("Source URL must be an HTTPS URL without embedded credentials")
    try:
        port = parsed_url.port
    except ValueError as exc:
        raise ValueError("Source URL has an invalid port") from exc
    if port not in (None, 443):
        raise ValueError("Source URL must use the standard HTTPS port")
    for file_name, file_hash in request.source_file_hashes.items():
        if not file_name.strip() or not re.fullmatch(r"[0-9a-fA-F]{64}", file_hash):
            raise ValueError("Each source_file_hashes entry needs a filename and a 64-character SHA-256")
    expected = REQUIRED_BY_SOURCE[request.source_id]
    dates = []
    years = []
    seen_rows = set()
    normalized = []
    for index, row in enumerate(request.observations):
        if not isinstance(row, dict):
            raise ValueError(f"Observation {index + 1} must be an object")
        required = {"variable", "value", "unit", "geography"}
        missing = required - row.keys()
        if missing:
            raise ValueError(f"Observation {index + 1} is missing: {', '.join(sorted(missing))}")
        variable = str(row["variable"])
        observed_at = None
        harvest_year = None
        if row.get("observed_at") is not None:
            try:
                observed_at = date.fromisoformat(str(row["observed_at"]))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Observation {index + 1} has an invalid ISO-8601 date") from exc
        if variable == "yield_t_per_ha":
            try:
                harvest_year = int(row["harvest_year"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Observation {index + 1} yield row requires an integer harvest_year") from exc
            if not 1900 <= harvest_year <= datetime.now(timezone.utc).year:
                raise ValueError(f"Observation {index + 1} harvest_year is outside the supported range")
        elif observed_at is None and request.source_id != "crop_calendar":
            raise ValueError(f"Observation {index + 1} requires observed_at")
        try:
            value = float(row["value"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Observation {index + 1} has an invalid numeric value") from exc
        if not math.isfinite(value):
            raise ValueError(f"Observation {index + 1} value must be finite")
        unit = str(row["unit"])
        if variable not in expected:
            raise ValueError(f"{request.source_id} does not accept variable {variable!r}")
        if unit not in ALLOWED_UNITS[variable]:
            raise ValueError(f"Unit {unit!r} is not accepted for {variable}")
        if not str(row["geography"]).strip():
            raise ValueError(f"Observation {index + 1} needs a geography label")
        if variable == "ndvi" and not -1 <= value <= 1:
            raise ValueError("NDVI values must be between -1 and 1")
        if variable == "soil_moisture" and unit == "m3/m3" and not 0 <= value <= 1:
            raise ValueError("Volumetric soil moisture must be between 0 and 1 m3/m3")
        if variable in {"crop_calendar_start_doy", "crop_calendar_end_doy"} and (not value.is_integer() or not 1 <= value <= 366):
            raise ValueError("Crop-calendar day-of-year values must be whole numbers between 1 and 366")
        if variable == "rainfall_mm" and value < 0:
            raise ValueError("rainfall_mm cannot be negative")
        if variable in {"tmin_c", "tmax_c"} and not -100 <= value <= 70:
            raise ValueError(f"{variable} is outside plausible physical bounds")
        if variable in {"yield_t_per_ha", "market_price_inr_per_quintal"} and value < 0:
            raise ValueError(f"{variable} cannot be negative")
        if request.source_id in {"satellite", "soil"}:
            try:
                latitude, longitude = float(row["latitude"]), float(row["longitude"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Observation {index + 1} requires latitude and longitude") from exc
            if not math.isfinite(latitude) or not -90 <= latitude <= 90 or not math.isfinite(longitude) or not -180 <= longitude <= 180:
                raise ValueError(f"Observation {index + 1} has coordinates outside valid bounds")
        if variable == "market_price_inr_per_quintal" and not str(row.get("market", "")).strip():
            raise ValueError(f"Observation {index + 1} requires the named market")
        if variable == "market_price_inr_per_quintal" and not str(row.get("commodity", "")).strip():
            raise ValueError(f"Observation {index + 1} requires a commodity label")
        if variable in {"yield_t_per_ha", "rainfall_mm", "tmax_c", "tmin_c", "crop_calendar_start_doy", "crop_calendar_end_doy"}:
            if not str(row.get("crop", "")).strip():
                raise ValueError(f"Observation {index + 1} requires a crop label")
            if not str(row.get("geography_id", "")).strip():
                raise ValueError(f"Observation {index + 1} requires a source geography_id")
        if request.source_id == "crop_calendar" and row.get("temporal_basis") != "static_primary_season":
            raise ValueError("Crop calendar rows must declare temporal_basis='static_primary_season'")
        if observed_at is not None:
            dates.append(observed_at.isoformat())
        if harvest_year is not None:
            years.append(harvest_year)
        key = (observed_at.isoformat() if observed_at else None, harvest_year, variable,
               str(row.get("geography_id", row["geography"])).strip().casefold(),
               str(row.get("crop", "")).strip().casefold(), str(row.get("market", "")).strip().casefold())
        if key in seen_rows:
            raise ValueError(f"Observation {index + 1} duplicates an earlier row at the same date/year and geography")
        seen_rows.add(key)
        normalized_row = {**row, "value": value,
                          "variable": variable, "unit": unit, "source_row_number": index + 1}
        if observed_at is not None:
            normalized_row["observed_at"] = observed_at.isoformat()
        if harvest_year is not None:
            normalized_row["harvest_year"] = harvest_year
        normalized.append(normalized_row)
    variables = {row["variable"] for row in normalized}
    if request.source_id == "cybench":
        missing_variables = REQUIRED_BY_SOURCE["cybench"] - variables
        if missing_variables:
            raise ValueError(f"CY-Bench pilot intake is incomplete; missing variables: {', '.join(sorted(missing_variables))}")
        pilot_yields = [row for row in normalized if row["variable"] == "yield_t_per_ha"
                        and row["harvest_year"] == 2015
                        and str(row.get("crop", "")).casefold() == "maize"
                        and "pune" in str(row.get("geography", "")).casefold()]
        if not pilot_yields:
            raise ValueError("CY-Bench pilot intake needs a Pune maize yield row for harvest year 2015")
        # F0's declared target is one Pune maize season. Require every day and all
        # weather variables so a partial export cannot masquerade as a season.
        weather = [row for row in normalized if row["variable"] in {"rainfall_mm", "tmax_c", "tmin_c"}]
        if weather:
            by_variable = {variable: set() for variable in ("rainfall_mm", "tmax_c", "tmin_c")}
            for row in weather:
                if not row.get("observed_at", "").startswith("2015-"):
                    raise ValueError("CY-Bench pilot weather must be dated within harvest year 2015")
                by_variable[row["variable"]].add(row["observed_at"])
            expected_dates = {(date(2015, 6, 1) + timedelta(days=offset)).isoformat()
                              for offset in range((date(2015, 10, 31) - date(2015, 6, 1)).days + 1)}
            if any(days != expected_dates for days in by_variable.values()):
                raise ValueError("CY-Bench pilot weather must cover every day from 2015-06-01 through 2015-10-31 for rainfall, tmin and tmax")
    if request.source_id == "crop_calendar" and variables != REQUIRED_BY_SOURCE["crop_calendar"]:
        raise ValueError("Crop-calendar intake must contain both start and end day-of-year values")
    payload = {"source_id": request.source_id, "source_url": request.source_url, "attribution": request.attribution,
               "license": request.license, "dataset_version": request.dataset_version, "geography": request.geography,
               "source_file_hashes": request.source_file_hashes,
               "observations": normalized}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(raw) > 5_000_000:
        raise ValueError("Normalized import exceeds the 5 MB snapshot limit")
    digest = hashlib.sha256(raw).hexdigest().upper()
    retrieved_at = datetime.now(timezone.utc).isoformat()
    snapshot_id = f"{request.source_id}-{digest[:16].lower()}-{uuid4().hex[:8]}"
    record = {"snapshot_id": snapshot_id, "source_id": request.source_id, "source_name": SOURCE_NAMES[request.source_id],
              "source_url": request.source_url, "attribution": request.attribution, "license": request.license,
              "dataset_version": request.dataset_version, "retrieved_at": retrieved_at, "content_sha256": digest,
              "retrieval_mode": "normalized_provider_export_import", "stale_fallback": False,
              "quality_status": "validated_pending_source_admission", "provenance_status": "self_reported_metadata",
              "schema_version": "sage-feature-snapshot-v2",
              "geography": request.geography, "row_count": len(normalized),
              "date_start": min(dates) if dates else None, "date_end": max(dates) if dates else None,
              "harvest_year_start": min(years) if years else None, "harvest_year_end": max(years) if years else None,
              "source_file_hashes": request.source_file_hashes,
              "variables": sorted(variables), "units": {key: sorted({row["unit"] for row in normalized if row["variable"] == key}) for key in variables},
              "coverage_complete": False, "assessment_use": "not_used_by_current_assessment_engine",
              "limitations": ["Provider metadata and license are self-reported and require review.",
                              "Normalized rows are not a matched crop-weather-price-credit panel.",
                              "Import does not validate source-specific archives or establish farm-level conditions."],
              "raw_body_utf8": raw.decode("utf-8"), "payload": payload}
    save_source_snapshot(snapshot_id, request.source_id, retrieved_at, digest, record)
    return record
