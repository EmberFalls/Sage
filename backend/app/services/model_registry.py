"""Allowlisted JSON yield fixtures; arbitrary serialized code is never loaded."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "models/yield/fixtures/illustrative-linear-v1.json"
FIXTURE_SHA256 = "11e727b029703eb8dd1e95cc7ee4706fcbd6141c36bb81aaef8d4c19b7329c58"
ARTIFACTS = {"illustrative-linear-v1": {"path": FIXTURE, "sha256": FIXTURE_SHA256,
                                         "registration_status": "registered_fixture_only"}}
EXPECTED_FEATURES = [
    {"name": "baseline_yield_t_per_ha", "type": "number", "unit": "t/ha"},
    {"name": "combined_loss_fraction", "type": "number", "unit": "fraction"},
    {"name": "baseline_yield_times_loss", "type": "number", "unit": "t/ha"},
]


class ArtifactError(ValueError):
    pass


def load_fixture(artifact_id: str | None = None, *, crop: str = "wheat", geography: str = "synthetic_demo_only") -> dict:
    if artifact_id is None:
        return {"status": "illustrative_fallback", "artifact_id": None, "sha256": None, "artifact": None}
    registration = ARTIFACTS.get(artifact_id)
    if not registration:
        raise ArtifactError("Artifact is not registered or is not operationally compatible")
    try:
        raw = registration["path"].read_bytes()
        artifact = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError("Artifact file is missing or invalid JSON") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if digest != registration["sha256"]:
        raise ArtifactError("Artifact checksum mismatch")
    if artifact.get("schema_version") != 1 or artifact.get("artifact_id") != artifact_id:
        raise ArtifactError("Artifact schema or identity mismatch")
    if artifact.get("artifact_type") != "yield_linear_fixture" or artifact.get("status") != "fixture_only":
        raise ArtifactError("Unsupported artifact type or status")
    if artifact.get("operational_admission") is not False or artifact.get("runtime", {}).get("format") != "JSON":
        raise ArtifactError("Only non-operational JSON fixtures are supported")
    if crop.casefold() not in artifact.get("coverage", {}).get("crops", []) or geography != artifact.get("coverage", {}).get("geography"):
        raise ArtifactError("Artifact crop or geography coverage mismatch")
    schema = artifact.get("feature_schema", [])
    coefficients = artifact.get("coefficients", [])
    if schema != EXPECTED_FEATURES:
        raise ArtifactError("Artifact feature order, type, or units mismatch")
    if len(coefficients) != len(schema) or any(not math.isfinite(float(x)) for x in coefficients):
        raise ArtifactError("Artifact feature schema or coefficients are invalid")
    example = artifact.get("inference_example", {})
    if len(example.get("features", [])) != len(schema) or artifact.get("evaluation_metadata", {}).get("status") != "illustrative_fixture":
        raise ArtifactError("Artifact handoff metadata or inference example is incomplete")
    return {"status": "fixture_only", "artifact_id": artifact_id, "sha256": digest, "artifact": artifact}


def predict_fixture(loaded: dict, baseline: float, loss: float) -> float:
    artifact = loaded["artifact"]
    features = [baseline, loss, baseline * loss]
    return float(artifact["intercept"]) + sum(float(w) * x for w, x in zip(artifact["coefficients"], features))
