import hashlib
import json

import pytest

from app.services import model_registry
from app.services.model_registry import ArtifactError, FIXTURE, load_fixture, predict_fixture
from app.services.satellite_ndvi import get_satellite_ndvi_telemetry
from app.services.soil_moisture import get_soil_moisture_telemetry
from app.schemas import ScenarioRequest
from app.services.assessment import evaluate_scenario


def test_satellite_and_soil_are_reported_missing_not_synthetic(monkeypatch):
    import urllib.error
    monkeypatch.setattr("app.services.soil_moisture.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")))
    monkeypatch.setattr("app.services.satellite_ndvi._post_json", lambda *args, **kwargs: {"features": []})
    from datetime import datetime, timedelta, timezone
    day = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    satellite = get_satellite_ndvi_telemetry([73.85, 18.52, 73.855, 18.525], day, day)
    soil = get_soil_moisture_telemetry("Pune")
    assert satellite["status"] == "unavailable" and satellite["ndvi"] is None
    assert satellite["cloud_cover_pct"] is None and satellite["assessment_use"] is False
    assert soil["status"] == "unavailable" and soil["assessment_use"] is False
    assert all(layer["value"] is None for layer in soil["layers"])


def test_soil_endpoint_returns_labeled_live_model_values(monkeypatch):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from app.services import soil_moisture
    local_now = datetime.now(ZoneInfo("Asia/Kolkata")).replace(minute=0, second=0, microsecond=0)
    times = [(local_now - timedelta(hours=12) + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(37)]
    variables = [value[0] for value in soil_moisture.VARIABLES.values()]
    payload = {"latitude": 18.5, "longitude": 73.8, "elevation": 560,
               "hourly": {"time": times, **{name: [0.2 + (i * 0.001) for i in range(37)] for name in variables},
                          "soil_temperature_0_to_7cm": [25.0] * 37}}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): pass
        def read(self, _limit): return json.dumps(payload).encode()
    monkeypatch.setattr(soil_moisture, "urlopen", lambda *_args, **_kwargs: Response())
    result = soil_moisture.get_soil_moisture_telemetry("Pune")
    assert result["status"] == "live_model_output"
    assert result["observation_type"] == "modeled_grid_output_not_farm_measurement"
    assert result["assessment_use"] is False
    assert result["layers"][0]["value"] is not None
    assert result["forecast_history"]


def test_allowlisted_json_fixture_is_checksum_and_schema_checked():
    artifact = load_fixture("illustrative-linear-v1")
    assert artifact["status"] == "fixture_only"
    assert artifact["sha256"] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert predict_fixture(artifact, 2.0, 0.2) == pytest.approx(1.6)
    with pytest.raises(ArtifactError, match="not registered"):
        load_fixture("untrusted-pickle")
    with pytest.raises(ArtifactError, match="coverage mismatch"):
        load_fixture("illustrative-linear-v1", crop="rice")


def test_fixture_bytes_have_expected_reviewed_checksum():
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == "11e727b029703eb8dd1e95cc7ee4706fcbd6141c36bb81aaef8d4c19b7329c58"


def test_fixture_runs_through_existing_scenario_evaluator_without_training():
    result = evaluate_scenario(ScenarioRequest(), model_artifact_id="illustrative-linear-v1")
    assert result["model_artifact"]["status"] == "fixture_only"
    assert result["stress"]["yield_projection"]["source_class"] == "illustrative_fixture"
    assert result["stress"]["yield_projection"]["status"] == "fixture_only_not_empirical"
    assert result["stress"]["yield_t_per_ha"] == result["stress"]["yield_projection"]["value"]


def test_incompatible_artifact_returns_visible_fallback():
    result = evaluate_scenario(ScenarioRequest(), model_artifact_id="research-pickle-v1")
    assert result["model_artifact"]["status"] == "rejected_fallback"
    assert result["stress"]["yield_projection"]["source_class"] == "illustrative_rule"


def test_registry_rejects_tampered_artifact_bytes(tmp_path, monkeypatch):
    tampered = tmp_path / "fixture.json"
    tampered.write_text(FIXTURE.read_text() + " ", encoding="utf-8")
    monkeypatch.setitem(model_registry.ARTIFACTS, "tampered", {"path": tampered, "sha256": model_registry.FIXTURE_SHA256})
    with pytest.raises(ArtifactError, match="checksum mismatch"):
        load_fixture("tampered")


def test_satellite_stats_integration_returns_area_quality(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from app.services import satellite_ndvi
    monkeypatch.setenv("CDSE_CLIENT_ID", "test-client")
    monkeypatch.setenv("CDSE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(satellite_ndvi, "_access_token", lambda: "test-token")
    responses = [
        {"features": [{"id": "scene-1", "properties": {"datetime": "2026-10-08T05:00:00Z", "eo:cloud_cover": 21.5}}]},
        {"status": "OK", "data": [{"interval": {"from": "2026-10-08T00:00:00Z"},
            "outputs": {"ndvi": {"bands": {"B0": {"stats": {"mean": 0.61, "sampleCount": 80, "noDataCount": 20}}}}}}]},
    ]
    calls = []
    def fake_post(url, body, **kwargs):
        calls.append((url, body, kwargs))
        return responses.pop(0)
    monkeypatch.setattr(satellite_ndvi, "_post_json", fake_post)
    observed = (datetime.now(timezone.utc).date() - timedelta(days=2)).isoformat()
    responses[0]["features"][0]["properties"]["datetime"] = f"{observed}T05:00:00Z"
    responses[1]["data"][0]["interval"]["from"] = f"{observed}T00:00:00Z"
    result = satellite_ndvi.get_satellite_ndvi_telemetry([73.85, 18.52, 73.855, 18.525], observed, observed)
    assert result["status"] == "live_observation"
    assert result["ndvi"] == 0.61
    assert result["clear_pixel_coverage_pct"] == 80
    assert result["assessment_use"] is False
    assert calls[1][0] == satellite_ndvi.STATS_URL
    assert calls[1][2]["token"] == "test-token"
