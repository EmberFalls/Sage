"""Source adapters with complete-window validation and immutable source snapshots."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from app.db import (list_source_refresh_events, list_source_snapshots, save_source_refresh_event,
                    save_source_snapshot)

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PATH = ROOT / "data" / "raw" / "open_meteo" / "pune_kharif_2015_sample.json"
SAMPLE_SHA256 = "D239158776E1277E2370E40DEDC96B25167AB4D41FC4CE0A13E55C6958E39ADD"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
SOURCE_ID = "open-meteo-pune-historical"
START_DATE = date(2015, 6, 1)
END_DATE = date(2015, 10, 31)
MODEL = "era5"
MAX_RESPONSE_BYTES = 2_000_000


def _expected_dates(start: date, end: date) -> list[str]:
    if end < start:
        raise ValueError("Weather end date must be on or after start date")
    return [(start + timedelta(days=offset)).isoformat() for offset in range((end - start).days + 1)]


def _validate_weather(payload: dict, *, complete_start: date | None = None,
                      complete_end: date | None = None) -> tuple[list[str], int]:
    if not isinstance(payload, dict):
        raise ValueError("Weather response must be a JSON object")
    daily = payload.get("daily")
    units = payload.get("daily_units")
    if not isinstance(daily, dict) or not isinstance(units, dict):
        raise ValueError("Weather response must contain daily values and units")
    required = ("time", "precipitation_sum", "temperature_2m_max", "temperature_2m_min")
    if any(key not in daily or key not in units for key in required):
        raise ValueError("Weather response is missing required daily fields or units")
    if any(not isinstance(daily[key], list) for key in required):
        raise ValueError("Weather daily fields must be arrays")
    lengths = {len(daily[key]) for key in required}
    if len(lengths) != 1 or not lengths or next(iter(lengths)) == 0:
        raise ValueError("Weather arrays must have the same non-zero row count")
    dates = daily["time"]
    try:
        parsed_dates = [date.fromisoformat(value) for value in dates]
    except (TypeError, ValueError) as exc:
        raise ValueError("Weather dates must use ISO-8601 calendar dates") from exc
    if parsed_dates != sorted(parsed_dates) or len(set(parsed_dates)) != len(parsed_dates):
        raise ValueError("Weather dates must be strictly increasing and unique")
    expected_units = {"time": "iso8601", "precipitation_sum": "mm",
                      "temperature_2m_max": "°C", "temperature_2m_min": "°C"}
    if any(units[key] != value for key, value in expected_units.items()):
        raise ValueError("Weather response units do not match the validated schema")
    for index, (rain, high, low) in enumerate(zip(daily["precipitation_sum"],
                                                   daily["temperature_2m_max"],
                                                   daily["temperature_2m_min"])):
        try:
            rain, high, low = float(rain), float(high), float(low)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Weather row {index + 1} has a missing or non-numeric value") from exc
        if not all(math.isfinite(value) for value in (rain, high, low)):
            raise ValueError(f"Weather row {index + 1} contains a non-finite value")
        if rain < 0 or low > high:
            raise ValueError(f"Weather row {index + 1} violates precipitation or temperature bounds")
    if complete_start is not None or complete_end is not None:
        if complete_start is None or complete_end is None:
            raise ValueError("A complete weather window requires both boundary dates")
        if dates != _expected_dates(complete_start, complete_end):
            raise ValueError("Weather archive does not cover every requested day exactly once")
    return dates, len(dates)


def _snapshot(raw: bytes, payload: dict, *, retrieval_mode: str, stale_fallback: bool,
              refresh_error: str | None = None) -> dict:
    dates, rows = _validate_weather(payload)
    digest = hashlib.sha256(raw).hexdigest().upper()
    retrieved = datetime.now(timezone.utc).isoformat()
    retrieval_key = retrieved.replace("-", "").replace(":", "").replace(".", "")
    snapshot_id = f"open-meteo-pune-{digest[:16].lower()}-{retrieval_key}"
    complete = (retrieval_mode == "live_archive_response" and
                dates == _expected_dates(START_DATE, END_DATE))
    error = refresh_error
    record = {
        "snapshot_id": snapshot_id,
        "source_id": SOURCE_ID,
        "source_name": "Open-Meteo Historical Weather API",
        "source_url": ARCHIVE_URL,
        "attribution": "Open-Meteo.com",
        "license": "CC-BY-4.0; free API is non-commercial only; verify current terms before other use",
        "retrieved_at": retrieved,
        "content_sha256": digest,
        "retrieval_mode": retrieval_mode,
        "stale_fallback": stale_fallback,
        "refresh_error": error,
        "provider_model": payload.get("model") or MODEL,
        "schema_version": "open-meteo-archive-daily-v1",
        "quality_status": "excerpt_only" if payload.get("sample_kind") == "excerpt_of_successful_api_response" else
                          "schema_validated_complete_window" if complete else "schema_validated_partial_window",
        "spatial_status": "grid_cell_not_farm_or_station",
        "geography": {"requested_latitude": payload.get("request", {}).get("latitude", 18.5204),
                      "requested_longitude": payload.get("request", {}).get("longitude", 73.8567),
                      "returned_latitude": payload.get("latitude"), "returned_longitude": payload.get("longitude"),
                      "elevation_m": payload.get("elevation")},
        "timezone": payload.get("timezone", "Asia/Kolkata"),
        "units": {key: payload["daily_units"][key] for key in ("precipitation_sum", "temperature_2m_max", "temperature_2m_min")},
        "temporal_resolution": "daily",
        "row_count": rows,
        "date_start": dates[0], "date_end": dates[-1],
        "requested_date_start": START_DATE.isoformat(), "requested_date_end": END_DATE.isoformat(),
        "coverage_complete": complete,
        "assessment_use": "not_used_by_current_assessment_engine",
        "limitations": ["ERA5 gridded historical reanalysis (about 25 km), not field/station observation.",
                        "Not a crop/yield/NDVI/price join.",
                        "A three-row excerpt is not a season archive." if rows <= 3 else
                        "A complete weather archive alone does not establish crop or borrower conditions."],
        "raw_body_utf8": raw.decode("utf-8"),
        "payload": payload,
    }
    save_source_snapshot(snapshot_id, SOURCE_ID, retrieved, digest, record)
    return record


def _fetch_archive(timeout_seconds: int) -> tuple[bytes, dict]:
    params = urlencode({"latitude": "18.5204", "longitude": "73.8567",
                        "start_date": START_DATE.isoformat(), "end_date": END_DATE.isoformat(),
                        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
                        "timezone": "Asia/Kolkata", "models": MODEL})
    request = Request(f"{ARCHIVE_URL}?{params}", headers={"Accept": "application/json", "User-Agent": "Sage-demo/1.0"})
    with urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("Weather response exceeds the 2 MB snapshot limit")
    payload = json.loads(raw)
    _validate_weather(payload, complete_start=START_DATE, complete_end=END_DATE)
    return raw, payload


def _record_refresh(status: str, snapshot_id: str | None, error_code: str | None = None) -> dict:
    record = {"refresh_id": f"SRC-{uuid4().hex[:16].upper()}", "source_id": SOURCE_ID,
              "attempted_at": datetime.now(timezone.utc).isoformat(), "status": status,
              "snapshot_id": snapshot_id, "error_code": error_code}
    save_source_refresh_event(record)
    return record


def refresh_pune_historical_weather(timeout_seconds: int = 10) -> dict:
    """Fetch the declared Pune season or return an explicitly labeled verified fallback."""
    try:
        raw, payload = _fetch_archive(timeout_seconds)
        snapshot = _snapshot(raw, payload, retrieval_mode="live_archive_response", stale_fallback=False)
        snapshot["refresh_event"] = _record_refresh("success", snapshot["snapshot_id"])
        return snapshot
    except Exception as live_error:
        error_code = type(live_error).__name__
        # Prefer a previously verified full archive over the three-row excerpt.
        cached = next((row for row in list_source_snapshots(SOURCE_ID, include_content=True)
                       if row.get("coverage_complete") and row.get("raw_body_utf8")), None)
        if cached:
            response = {**cached, "retrieval_mode": "cached_verified_archive_fallback", "stale_fallback": True,
                        "refresh_error": f"Live refresh unavailable or invalid: {error_code}",
                        "fallback_snapshot_id": cached["snapshot_id"]}
            response["refresh_event"] = _record_refresh("cached_fallback", cached["snapshot_id"], error_code)
            return response
        raw = SAMPLE_PATH.read_bytes().replace(b"\r\n", b"\n")
        digest = hashlib.sha256(raw).hexdigest().upper()
        if digest != SAMPLE_SHA256:
            _record_refresh("failed_no_fallback", None, "fallback_checksum_mismatch")
            raise RuntimeError("The retained Open-Meteo fallback failed its frozen SHA-256 check") from live_error
        payload = json.loads(raw)
        snapshot = _snapshot(raw, payload, retrieval_mode="verified_local_excerpt_fallback", stale_fallback=True,
                             refresh_error=error_code)
        snapshot["refresh_event"] = _record_refresh("excerpt_fallback", snapshot["snapshot_id"], error_code)
        return snapshot


def list_data_sources() -> dict:
    snapshots = list_source_snapshots()
    latest = {}
    for record in snapshots:
        latest.setdefault(record["source_id"], record)
    events = list_source_refresh_events()
    last_refresh = {}
    for event in events:
        last_refresh.setdefault(event["source_id"], event)
    imported = lambda source_id, fallback: {
        "status": latest[source_id]["quality_status"] if source_id in latest else fallback,
        "latest_snapshot": latest.get(source_id),
    }
    # Diagnostic only: imported/pending rows are not admitted to the runtime.
    # Exact source geography, crop, year and date overlap are required even to
    # call something a candidate join.
    cybench = next((row for row in list_source_snapshots("cybench", include_content=True)
                    if row.get("quality_status") == "validated_pending_source_admission"), None)
    weather = latest.get(SOURCE_ID)
    join_status = "blocked_missing_admitted_matched_rows"
    join_detail = "No reviewed CY-Bench pilot snapshot is available."
    if cybench:
        observations = (cybench.get("payload") or {}).get("observations", [])
        yields = [row for row in observations if row.get("variable") == "yield_t_per_ha"
                  and str(row.get("crop", "")).casefold() == "maize"
                  and row.get("harvest_year") == 2015
                  and str(row.get("geography_id", "")).strip()]
        if weather and weather.get("coverage_complete") and len(yields) == 1:
            join_status = "candidate_parts_present_not_matched"
            join_detail = "A normalized 2015 maize yield candidate and complete Pune-grid weather archive exist, but district-to-grid alignment and upstream provenance/license are unverified; this is not a matched join."
        else:
            join_status = "candidate_incomplete_or_weather_missing"
            join_detail = "A pending CY-Bench export exists, but the required single 2015 maize yield candidate and complete dated weather archive are not both present."
    weather_status = ("verified_excerpt_available" if SOURCE_ID not in latest else
                      "verified_excerpt_fallback" if latest[SOURCE_ID].get("quality_status") == "excerpt_only" else
                      "complete_archive_available" if latest[SOURCE_ID].get("coverage_complete") and
                      latest[SOURCE_ID].get("retrieval_mode") == "live_archive_response" else
                      "cached_complete_archive" if latest[SOURCE_ID].get("coverage_complete") else "partial_archive")
    return {
        "sources": [
            {"source_id": SOURCE_ID, "name": "Open-Meteo Historical Weather API",
             "status": weather_status, "version": MODEL, "url": ARCHIVE_URL, "attribution": "Open-Meteo.com",
             "license": "CC-BY-4.0; free API non-commercial terms apply", "spatial_resolution": "returned grid cell",
             "temporal_resolution": "daily", "units": {"precipitation_sum": "mm", "temperature_2m_max": "°C", "temperature_2m_min": "°C"},
             "latest_snapshot": latest.get(SOURCE_ID), "last_refresh": last_refresh.get(SOURCE_ID),
             "runtime_assessment_use": "conditional_stage_features_only_when_date_and_Pune_geography_overlap",
             "note": "The retained ERA5 fixture contributes dated per-stage summaries only for matching Pune crop windows and is clipped at assessment as-of; it is not a farm observation or yield model predictor."},
            {"source_id": "cybench", "name": "CY-Bench", **imported("cybench", "archive_not_inspected"),
             "url": "https://zenodo.org/records/17279151", "version": "1.10",
             "runtime_assessment_use": False,
             "note": "The current archive is 6.2 GB. Import only a documented India maize subset; verify Pune administrative IDs and dataset/source licenses before admission."},
            {"source_id": "maharashtra-apy-pune-maize-2015-16", "name": "Maharashtra district APY — Pune Kharif maize 2015-16",
             "status": "candidate_not_admitted", "url": "https://www.scribd.com/document/1004670718/DISTRICTWISE-APY-2015-16",
             "candidate_value": {"yield": 852, "unit": "kg/ha", "period": "Kharif 2015-16"},
             "runtime_assessment_use": False,
             "note": "Third-party mirror only. Primary report bytes/checksum and reuse terms are unverified; district-to-weather-grid crosswalk is missing. See data/raw/agriculture/pune_maize_2015_16_candidate.json."},
            {"source_id": "agmarknet", "name": "AGMARKNET", **imported("agmarknet", "endpoint_and_rows_unverified"),
             "url": "https://data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi",
             "runtime_assessment_use": False},
            {"source_id": "satellite", "name": "Satellite / NDVI", **imported("satellite", "unavailable"),
             "runtime_assessment_use": False, "note": "Copernicus Sentinel data are open; no farm boundary or validated Pune pixel series is admitted."},
            {"source_id": "soil", "name": "Soil moisture", **imported("soil", "unavailable"),
             "runtime_assessment_use": False},
            {"source_id": "crop_calendar", "name": "Crop calendar", **imported("crop_calendar", "unavailable"),
             "url": "https://zenodo.org/records/7875105", "version": "WorldCereal primary-season calendar",
             "runtime_assessment_use": False,
             "note": "No Pune maize calendar raster or administrative extraction is admitted; static calendar rows require source, grid/boundary metadata, and no implied year."},
            {"source_id": "crop-yield-price-join", "name": "Pune maize season join", "status": join_status,
             "note": join_detail, "runtime_assessment_use": False},
        ],
        "snapshots": snapshots,
        "recent_refreshes": events[:20],
        "claim_limit": "A weather grid-cell snapshot is not evidence of farm conditions or a matched crop-yield-credit dataset.",
    }
