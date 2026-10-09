"""Farm-bounding-box Sentinel-2 L2A NDVI statistics via Copernicus Data Space."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
STAC_URL = "https://stac.dataspace.copernicus.eu/v1/search"
STATS_URL = "https://sh.dataspace.copernicus.eu/statistics/v1"
_TOKEN: str | None = None
_TOKEN_EXPIRY = datetime.min.replace(tzinfo=timezone.utc)
_TOKEN_LOCK = threading.Lock()
MAX_BODY_BYTES = 1_500_000

EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "B08", "SCL", "dataMask"] }],
    output: [
      { id: "ndvi", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1, sampleType: "UINT8" }
    ]
  };
}
function evaluatePixel(samples) {
  const cloudOrInvalid = [0, 3, 8, 9, 10, 11].includes(samples.SCL);
  const clear = samples.dataMask === 1 && !cloudOrInvalid;
  const denominator = samples.B08 + samples.B04;
  const value = clear && denominator !== 0 ? (samples.B08 - samples.B04) / denominator : 0;
  return { ndvi: [value], dataMask: [clear ? 1 : 0] };
}
"""


def _post_json(url: str, body: dict, *, token: str | None = None, timeout: int = 25) -> dict:
    headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Sage-telemetry/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(MAX_BODY_BYTES + 1)
    if len(payload) > MAX_BODY_BYTES:
        raise ValueError("provider response too large")
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise ValueError("invalid provider response")
    return parsed


def _access_token() -> str:
    global _TOKEN, _TOKEN_EXPIRY
    client_id = os.getenv("CDSE_CLIENT_ID", "").strip()
    client_secret = os.getenv("CDSE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError("Copernicus Data Space credentials are not configured")
    with _TOKEN_LOCK:
        now = datetime.now(timezone.utc)
        if _TOKEN and _TOKEN_EXPIRY > now + timedelta(minutes=2):
            return _TOKEN
        encoded = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": client_id,
                                          "client_secret": client_secret}).encode("ascii")
        request = urllib.request.Request(TOKEN_URL, data=encoded,
                                         headers={"Content-Type": "application/x-www-form-urlencoded",
                                                  "Accept": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read(100_000))
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("Copernicus token response was invalid")
        _TOKEN = token
        _TOKEN_EXPIRY = now + timedelta(seconds=max(60, int(payload.get("expires_in", 300)) - 60))
        return token


def _validate_bbox(bbox: list[float]) -> list[float]:
    if len(bbox) != 4:
        raise ValueError("Bounding box needs west, south, east, north coordinates")
    west, south, east, north = [float(item) for item in bbox]
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Bounding box coordinates are invalid")
    # Bound cost and accidental broad-area queries. A 0.02 degree limit is
    # roughly 2.2 km at the equator and smaller east-west in India.
    if east - west > 0.02 or north - south > 0.02:
        raise ValueError("Farm bounding box is too large (maximum 0.02° per side)")
    return [west, south, east, north]


def _unavailable(bbox: list[float] | None, start: str, end: str, reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "source": "Copernicus Sentinel-2 L2A", "bbox": bbox,
            "date_range": {"from": start, "to": end}, "ndvi": None, "cloud_cover_pct": None,
            "clear_pixel_coverage_pct": None, "resolution_meters": 10, "scene_count": 0,
            "reason": reason, "assessment_use": False}


def get_satellite_ndvi_telemetry(bbox: list[float], start_date: str, end_date: str,
                                 max_scene_cloud_pct: float = 80) -> dict[str, Any]:
    """Return a clear-pixel NDVI mean for an explicitly supplied small farm bbox."""
    try:
        bounds = _validate_bbox(bbox)
        start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
        if end < start or (end - start).days > 30:
            return _unavailable(bounds, start_date, end_date, "Choose a date window no longer than 31 days.")
        if end > datetime.now(timezone.utc).date():
            return _unavailable(bounds, start_date, end_date, "Future satellite dates are not available.")
        if not 0 <= float(max_scene_cloud_pct) <= 100:
            return _unavailable(bounds, start_date, end_date, "Cloud-cover limit must be between 0 and 100 percent.")
    except (TypeError, ValueError):
        return _unavailable(None, str(start_date), str(end_date), "Bounding box or date inputs are invalid.")

    bbox_tuple = tuple(bounds)
    stac_payload = {"collections": ["sentinel-2-l2a"], "bbox": list(bbox_tuple),
                    "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
                    "limit": 100, "query": {"eo:cloud_cover": {"lte": float(max_scene_cloud_pct)}}}
    try:
        stac = _post_json(STAC_URL, stac_payload, timeout=20)
        features = stac.get("features", [])
        if not features:
            return _unavailable(bounds, start.isoformat(), end.isoformat(), "No Sentinel-2 L2A scene met the date, area, and scene-cloud filter.")
        if not os.getenv("CDSE_CLIENT_ID") or not os.getenv("CDSE_CLIENT_SECRET"):
            return _unavailable(bounds, start.isoformat(), end.isoformat(),
                                "Scenes are discoverable, but NDVI processing is not configured. Set server-side CDSE_CLIENT_ID and CDSE_CLIENT_SECRET.") | {
                                    "scene_count": len(features), "scene_cloud_cover_pct": min(
                                        float(item.get("properties", {}).get("eo:cloud_cover", 100)) for item in features)}
        token = _access_token()
        stats_request = {
            "input": {"bounds": {"bbox": bounds, "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"}},
                      "data": [{"type": "sentinel-2-l2a", "dataFilter": {
                          "timeRange": {"from": f"{start.isoformat()}T00:00:00Z", "to": f"{end.isoformat()}T23:59:59Z"},
                          "maxCloudCoverage": float(max_scene_cloud_pct), "mosaickingOrder": "leastCC"}}]},
            "aggregation": {"timeRange": {"from": f"{start.isoformat()}T00:00:00Z", "to": f"{end.isoformat()}T23:59:59Z"},
                            "aggregationInterval": {"of": "P1D"}, "evalscript": EVALSCRIPT, "resx": 10, "resy": 10},
        }
        stats = _post_json(STATS_URL, stats_request, token=token, timeout=45)
        observations = []
        for row in stats.get("data", []):
            band = row.get("outputs", {}).get("ndvi", {}).get("bands", {}).get("B0", {}).get("stats", {})
            if band.get("sampleCount", 0) and isinstance(band.get("mean"), (int, float)):
                count = int(band["sampleCount"])
                missing = int(band.get("noDataCount", 0))
                observations.append({"date": row.get("interval", {}).get("from", "")[:10],
                                     "mean_ndvi": round(float(band["mean"]), 4), "clear_pixel_count": count,
                                     "no_data_or_cloud_pixel_count": missing,
                                     "clear_pixel_coverage_pct": round(100 * count / max(1, count + missing), 1)})
        if not observations:
            return _unavailable(bounds, start.isoformat(), end.isoformat(), "No clear, valid pixels were returned for this plot and date window.") | {
                "scene_count": len(features)}
        latest = observations[-1]
        item_clouds = [float(item.get("properties", {}).get("eo:cloud_cover")) for item in features
                       if isinstance(item.get("properties", {}).get("eo:cloud_cover"), (int, float))]
        return {"status": "live_observation", "source": "Copernicus Sentinel-2 L2A via Data Space Statistical API",
                "collection": "sentinel-2-l2a", "bbox": bounds, "date_range": {"from": start.isoformat(), "to": end.isoformat()},
                "observation_date": latest["date"], "ndvi": latest["mean_ndvi"], "unit": "unitless (-1 to 1)",
                "cloud_cover_pct": round(min(item_clouds), 1) if item_clouds else None,
                "cloud_cover_semantics": "minimum scene-wide cloud percentage among returned intersecting scenes; not plot cloud percentage",
                "clear_pixel_coverage_pct": latest["clear_pixel_coverage_pct"],
                "clear_pixel_count": latest["clear_pixel_count"],
                "no_data_or_cloud_pixel_count": latest["no_data_or_cloud_pixel_count"],
                "resolution_meters": 10, "scene_count": len(features), "scenes": [
                    {"id": item.get("id"), "datetime": item.get("properties", {}).get("datetime"),
                     "cloud_cover_pct": item.get("properties", {}).get("eo:cloud_cover")}
                    for item in features[:10]], "daily_series": observations,
                "observation_type": "satellite_pixel_derived_area_mean_not_ground_sensor",
                "assessment_use": False,
                "limitations": ["The supplied rectangle is a plot-area proxy; exclude roads, roofs, and neighboring fields when drawing it.",
                                "Scene-level cloud percentage differs from clear-pixel coverage over this plot.",
                                "NDVI is not a direct yield estimate and is not used in credit assessment."]}
    except Exception as exc:
        return _unavailable(bounds, start.isoformat(), end.isoformat(),
                            f"Copernicus data could not be retrieved ({type(exc).__name__}).")
