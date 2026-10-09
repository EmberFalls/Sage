import hashlib
import json
import os
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.schemas import ScenarioRequest
from app.services import model_registry, satellite_ndvi, soil_moisture
from app.services.assessment import evaluate_scenario
from app.services.model_registry import ArtifactError, FIXTURE, load_fixture, predict_fixture
from app.services.satellite_ndvi import get_satellite_ndvi_telemetry
from app.services.soil_moisture import get_soil_moisture_telemetry


class F11AdmissionAndArtifactsTests(unittest.TestCase):
    def test_satellite_and_soil_are_reported_missing_not_synthetic(self):
        def raise_urllib(*_args, **_kwargs):
            raise urllib.error.URLError("offline")

        with patch.object(soil_moisture, "urlopen", side_effect=raise_urllib), \
             patch.object(satellite_ndvi, "_post_json", return_value={"features": []}):
            day = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
            satellite = get_satellite_ndvi_telemetry([73.85, 18.52, 73.855, 18.525], day, day)
            soil = get_soil_moisture_telemetry("Pune")
            self.assertEqual(satellite["status"], "unavailable")
            self.assertIsNone(satellite["ndvi"])
            self.assertIsNone(satellite["cloud_cover_pct"])
            self.assertFalse(satellite["assessment_use"])
            self.assertEqual(soil["status"], "unavailable")
            self.assertFalse(soil["assessment_use"])
            self.assertTrue(all(layer["value"] is None for layer in soil["layers"]))

    def test_soil_endpoint_returns_labeled_live_model_values(self):
        local_now = datetime.now(ZoneInfo("Asia/Kolkata")).replace(minute=0, second=0, microsecond=0)
        times = [(local_now - timedelta(hours=12) + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(37)]
        variables = [value[0] for value in soil_moisture.VARIABLES.values()]
        payload = {
            "latitude": 18.5, "longitude": 73.8, "elevation": 560,
            "hourly": {"time": times, **{name: [0.2 + (i * 0.001) for i in range(37)] for name in variables},
                       "soil_temperature_0_to_7cm": [25.0] * 37}
        }

        class Response:
            def __enter__(self): return self
            def __exit__(self, *_args): pass
            def read(self, _limit=None): return json.dumps(payload).encode()

        with patch.object(soil_moisture, "urlopen", return_value=Response()):
            result = soil_moisture.get_soil_moisture_telemetry("Pune")
            self.assertEqual(result["status"], "live_model_output")
            self.assertEqual(result["observation_type"], "modeled_grid_output_not_farm_measurement")
            self.assertFalse(result["assessment_use"])
            self.assertIsNotNone(result["layers"][0]["value"])
            self.assertTrue(result["forecast_history"])

    def test_allowlisted_json_fixture_is_checksum_and_schema_checked(self):
        artifact = load_fixture("illustrative-linear-v1")
        self.assertEqual(artifact["status"], "fixture_only")
        self.assertEqual(artifact["sha256"], hashlib.sha256(FIXTURE.read_bytes()).hexdigest())
        self.assertAlmostEqual(predict_fixture(artifact, 2.0, 0.2), 1.6, places=5)
        with self.assertRaisesRegex(ArtifactError, "not registered"):
            load_fixture("untrusted-pickle")
        with self.assertRaisesRegex(ArtifactError, "coverage mismatch"):
            load_fixture("illustrative-linear-v1", crop="rice")

    def test_fixture_bytes_have_expected_reviewed_checksum(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), "11e727b029703eb8dd1e95cc7ee4706fcbd6141c36bb81aaef8d4c19b7329c58")

    def test_fixture_runs_through_existing_scenario_evaluator_without_training(self):
        result = evaluate_scenario(ScenarioRequest(), model_artifact_id="illustrative-linear-v1")
        self.assertEqual(result["model_artifact"]["status"], "fixture_only")
        self.assertEqual(result["stress"]["yield_projection"]["source_class"], "illustrative_fixture")
        self.assertEqual(result["stress"]["yield_projection"]["status"], "fixture_only_not_empirical")
        self.assertEqual(result["stress"]["yield_t_per_ha"], result["stress"]["yield_projection"]["value"])

    def test_incompatible_artifact_returns_visible_fallback(self):
        result = evaluate_scenario(ScenarioRequest(), model_artifact_id="research-pickle-v1")
        self.assertEqual(result["model_artifact"]["status"], "rejected_fallback")
        self.assertEqual(result["stress"]["yield_projection"]["source_class"], "illustrative_rule")

    def test_registry_rejects_tampered_artifact_bytes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tampered = Path(tmp_dir) / "fixture.json"
            tampered.write_text(FIXTURE.read_text() + " ", encoding="utf-8")
            with patch.dict(model_registry.ARTIFACTS, {"tampered": {"path": tampered, "sha256": model_registry.FIXTURE_SHA256}}):
                with self.assertRaisesRegex(ArtifactError, "checksum mismatch"):
                    load_fixture("tampered")

    def test_satellite_stats_integration_returns_area_quality(self):
        responses = [
            {"features": [{"id": "scene-1", "properties": {"datetime": "2026-10-08T05:00:00Z", "eo:cloud_cover": 21.5}}]},
            {"status": "OK", "data": [{"interval": {"from": "2026-10-08T00:00:00Z"},
                "outputs": {"ndvi": {"bands": {"B0": {"stats": {"mean": 0.61, "sampleCount": 80, "noDataCount": 20}}}}}}]},
        ]
        calls = []

        def fake_post(url, body, **kwargs):
            calls.append((url, body, kwargs))
            return responses.pop(0)

        with patch.dict(os.environ, {"CDSE_CLIENT_ID": "test-client", "CDSE_CLIENT_SECRET": "test-secret"}), \
             patch.object(satellite_ndvi, "_access_token", return_value="test-token"), \
             patch.object(satellite_ndvi, "_post_json", side_effect=fake_post):
            observed = (datetime.now(timezone.utc).date() - timedelta(days=2)).isoformat()
            responses[0]["features"][0]["properties"]["datetime"] = f"{observed}T05:00:00Z"
            responses[1]["data"][0]["interval"]["from"] = f"{observed}T00:00:00Z"
            result = satellite_ndvi.get_satellite_ndvi_telemetry([73.85, 18.52, 73.855, 18.525], observed, observed)
            self.assertEqual(result["status"], "live_observation")
            self.assertEqual(result["ndvi"], 0.61)
            self.assertEqual(result["clear_pixel_coverage_pct"], 80)
            self.assertFalse(result["assessment_use"])
            self.assertEqual(calls[1][0], satellite_ndvi.STATS_URL)
            self.assertEqual(calls[1][2]["token"], "test-token")
