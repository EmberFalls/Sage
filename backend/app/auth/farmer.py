"""Authenticated farmer projections and immutable report downloads."""
import csv
import io
import json
import textwrap
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Literal

from app.auth.dependencies import get_current_user
from app.db import (add_audit_event, create_farmer_request, get_borrower_record,
                    get_farmer_request, get_scenario, list_farmer_requests, list_scenarios,
                    review_farmer_request, save_scenario)
from app.schemas import ScenarioRequest
from app.services.assessment import evaluate_scenario
from app.config import APP_MODE

router = APIRouter(prefix="/api/private", tags=["Authenticated farmer"])


def pdf_escape(line: str) -> str:
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def farmer_borrower(user: dict) -> tuple[str, dict]:
    if user.get("role") != "farmer" or not user.get("linked_borrower_id"):
        raise HTTPException(403, "Farmer access required")
    borrower_id = user["linked_borrower_id"]
    borrower = get_borrower_record(borrower_id)
    if borrower is None:
        raise HTTPException(404, "Farmer record not found")
    return borrower_id, borrower


def latest_assessment(borrower_id: str) -> dict | None:
    for summary in list_scenarios(100):
        if summary["borrower_id"] == borrower_id:
            return get_scenario(summary["scenario_id"])
    return None


def farmer_projection(borrower: dict, result: dict | None) -> dict:
    projection = {
        "mode": "synthetic_demo" if APP_MODE == "demo" else "hosted_authenticated",
        "farmer": {"id": borrower["id"], "name": borrower.get("alias"), "district": borrower.get("district"),
                   "crop": borrower.get("crop"), "area_ha": borrower.get("area_ha"),
                   "sowing_date": borrower.get("sowing_date"), "harvest_date": borrower.get("harvest_date")},
        "assessment": None,
        "help": {"simulation": "This estimate is a planning aid, not a bank decision or forecast.",
                 "missing_evidence": ["verified yield history", "confirmed market price", "issued local weather forecast"],
                 "actions": "Contact your branch before changing repayment plans."},
    }
    if not result:
        projection["help"]["empty"] = "No saved assessment is available yet. Your branch can create one."
        return projection
    stress = result.get("stress", {})
    projection["assessment"] = {
        "id": result["scenario_id"], "borrower_id": result["borrower_id"],
        "result_hash": result.get("result_hash"),
        "as_of": result.get("assessment_as_of"), "created_at": result.get("created_at"),
        "engine_version": result.get("engine_version"), "source_versions": result.get("source_versions", {}),
        "crop": borrower.get("crop"), "yield_t_per_ha": stress.get("yield_t_per_ha"),
        "gross_revenue_inr": stress.get("gross_revenue_inr"), "due_date": stress.get("due_date"),
        "due_inr": stress.get("due_inr"), "cash_pre_due_inr": stress.get("cash_pre_due_inr"),
        "cash_gap_inr": stress.get("cash_gap_inr"), "cash_after_due_inr": stress.get("cash_after_due_inr"),
        "action_status": result.get("action_status"), "input_data_status": result.get("input_data_status", {}),
        "assumptions": result.get("drivers", []), "limitations": result.get("warnings", []),
        "inputs": {key: value for key, value in result.get("scenario_request", {}).items()
                   if key in {"borrower_id", "as_of", "loan_principal_override_inr", "overrides", "action_id", "action_parameters"}},
        "totals": {name: {key: result.get(name, {}).get(key) for key in
                           ("gross_revenue_inr", "cash_pre_due_inr", "due_inr", "cash_gap_inr", "cash_after_due_inr")}
                   for name in ("baseline", "stress", "stress_with_action") if result.get(name)},
        "snapshot_freshness": result.get("snapshot_freshness", "saved"),
        "human_review_status": "not reviewed",
        "eligible_options": [{"id": row.get("candidate_id"), "label": row.get("label") or row.get("name") or row.get("candidate_id"),
                              "eligible": bool(row.get("eligible"))}
                             for row in result.get("action_candidates", [])],
    }
    return projection


@router.get("/farmer/home")
def farmer_home(user: dict = Depends(get_current_user)):
    borrower_id, borrower = farmer_borrower(user)
    result = latest_assessment(borrower_id)
    add_audit_event(actor_id=user["id"], actor_role=user["role"], entity_type="assessment",
                    entity_id=(result or {}).get("scenario_id", borrower_id), action="read_farmer_home",
                    reason="Farmer viewed own saved assessment", result_ref=(result or {}).get("result_hash"))
    return farmer_projection(borrower, result)


@router.get("/farmer/assessments/{assessment_id}")
def farmer_assessment(assessment_id: str, user: dict = Depends(get_current_user)):
    borrower_id, borrower = farmer_borrower(user)
    result = get_scenario(assessment_id)
    if result is None or result.get("borrower_id") != borrower_id:
        raise HTTPException(404, "Assessment not found")
    add_audit_event(actor_id=user["id"], actor_role=user["role"], entity_type="assessment",
                    entity_id=assessment_id, action="read_farmer_assessment", reason="Farmer viewed own assessment",
                    result_ref=result.get("result_hash"))
    return farmer_projection(borrower, result)


class FarmerRequest(BaseModel):
    assessment_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=3, max_length=1000)


@router.post("/farmer/requests", status_code=201)
def farmer_create_request(payload: FarmerRequest, user: dict = Depends(get_current_user)):
    borrower_id, _ = farmer_borrower(user)
    assessment = get_scenario(payload.assessment_id)
    if assessment is None or assessment.get("borrower_id") != borrower_id:
        raise HTTPException(404, "Assessment not found")
    request = create_farmer_request(f"FR-{uuid4().hex[:12].upper()}", user["id"], borrower_id,
                                    payload.assessment_id, payload.message.strip())
    add_audit_event(actor_id=user["id"], actor_role=user["role"], entity_type="farmer_request",
                    entity_id=request["request_id"], action="create", reason="Farmer requested branch review",
                    result_ref=payload.assessment_id)
    return request


@router.get("/farmer/requests")
def farmer_requests(user: dict = Depends(get_current_user)):
    farmer_borrower(user)
    return {"requests": list_farmer_requests(user["id"])}


def scoped_request(user: dict, request_id: str) -> dict:
    request = get_farmer_request(request_id)
    if request is None:
        raise HTTPException(404, "Request not found")
    if user.get("role") == "admin":
        return request
    if user.get("role") not in {"bank_officer", "branch_lead"} or not user.get("branch_id"):
        raise HTTPException(403, "Branch-scoped review access required")
    borrower = get_borrower_record(request["borrower_id"])
    if borrower is None or borrower.get("branch") != user["branch_id"]:
        raise HTTPException(404, "Request not found")
    return request


@router.get("/review/requests")
def review_queue(user: dict = Depends(get_current_user)):
    if user.get("role") == "admin":
        rows = list_farmer_requests()
    elif user.get("role") in {"bank_officer", "branch_lead"} and user.get("branch_id"):
        rows = [row for row in list_farmer_requests() if
                (get_borrower_record(row["borrower_id"]) or {}).get("branch") == user["branch_id"]]
    else:
        raise HTTPException(403, "Branch-scoped review access required")
    return {"requests": rows}


class RequestReview(BaseModel):
    status: Literal["under_review", "needs_information", "reviewed"]
    note: str = Field(min_length=3, max_length=1000)


@router.patch("/review/requests/{request_id}")
def review_request(request_id: str, payload: RequestReview, user: dict = Depends(get_current_user)):
    row = scoped_request(user, request_id)
    if row["status"] not in {"open", "under_review", "needs_information"}:
        raise HTTPException(409, "Request is already closed")
    updated = review_farmer_request(request_id, status=payload.status, reviewer_id=user["id"], note=payload.note.strip())
    add_audit_event(actor_id=user["id"], actor_role=user["role"], entity_type="farmer_request",
                    entity_id=request_id, action="review", reason="Reviewer updated request status",
                    result_ref=row["assessment_id"])
    return updated


def require_officer(user: dict) -> None:
    if user.get("role") not in {"bank_officer", "branch_lead", "admin"}:
        raise HTTPException(403, "Officer access required")


def officer_can_access_borrower(user: dict, borrower_id: str) -> dict:
    require_officer(user)
    borrower = get_borrower_record(borrower_id)
    if borrower is None:
        raise HTTPException(404, "Record not found")
    if user.get("role") == "admin":
        return borrower
    if not user.get("branch_id"):
        raise HTTPException(403, "A provisioned branch is required")
    if borrower.get("branch") != user["branch_id"]:
        raise HTTPException(404, "Record not found")
    return borrower


def officer_can_access_assessment(user: dict, assessment_id: str) -> dict:
    result = get_scenario(assessment_id)
    if result is None:
        raise HTTPException(404, "Assessment not found")
    officer_can_access_borrower(user, result["borrower_id"])
    return result


@router.post("/officer/assessments/evaluate")
def officer_evaluate(payload: ScenarioRequest, user: dict = Depends(get_current_user)):
    officer_can_access_borrower(user, payload.borrower_id)
    try:
        result = evaluate_scenario(payload)
    except (KeyError, ValueError) as exc:
        raise HTTPException(422, "Assessment could not be calculated") from exc
    saved = save_scenario(result["scenario_id"], payload.borrower_id, result["input_hash"],
                          payload.model_dump(mode="json"), result)
    add_audit_event(actor_id=user["id"], actor_role=user["role"], entity_type="assessment",
                    entity_id=saved["scenario_id"], action="evaluate", reason="Authorized branch assessment",
                    result_ref=saved.get("result_hash"))
    return saved


@router.get("/officer/assessments")
def officer_assessments(limit: int = Query(default=50, ge=1, le=100), user: dict = Depends(get_current_user)):
    require_officer(user)
    if user.get("role") != "admin" and not user.get("branch_id"):
        raise HTTPException(403, "A provisioned branch is required")
    rows = list_scenarios(limit)
    if user.get("role") != "admin":
        rows = [row for row in rows if (get_borrower_record(row["borrower_id"]) or {}).get("branch") == user["branch_id"]]
    return {"assessments": rows}


@router.get("/officer/assessments/{assessment_id}")
def officer_assessment(assessment_id: str, user: dict = Depends(get_current_user)):
    result = officer_can_access_assessment(user, assessment_id)
    add_audit_event(actor_id=user["id"], actor_role=user["role"], entity_type="assessment",
                    entity_id=assessment_id, action="read_officer_assessment", reason="Authorized assessment review",
                    result_ref=result.get("result_hash"))
    return result


@router.get("/officer/reports/{assessment_id}")
def officer_report(assessment_id: str, format: str = Query(default="json", pattern="^(json|csv|pdf)$"),
                  user: dict = Depends(get_current_user)):
    result = officer_can_access_assessment(user, assessment_id)
    record = {"assessment_id": assessment_id, "as_of": result.get("assessment_as_of"),
              "inputs": result.get("scenario_request"), "assumptions": result.get("drivers"),
              "sources": result.get("source_versions"), "engine_version": result.get("engine_version"),
              "limitations": result.get("warnings"), "human_review_status": "not reviewed",
              "report_scope": "simulation result; available evidence only", "result": result}
    add_audit_event(actor_id=user["id"], actor_role=user["role"], entity_type="report",
                    entity_id=assessment_id, action=f"officer_download_{format}", reason="Authorized branch report download",
                    result_ref=result.get("result_hash"))
    filename = f"sage-{assessment_id}.{format}"
    if format == "json":
        return Response(json.dumps(record, ensure_ascii=False, indent=2), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "private, no-store"})
    if format == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["field", "json_value"])
        for key, value in record.items():
            writer.writerow([key, json.dumps(value, ensure_ascii=False)])
        return Response(output.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "private, no-store"})
    lines = ["Sage officer assessment report", f"Assessment ID: {assessment_id}",
             f"As of: {record['as_of']}", f"Result hash: {result.get('result_hash')}",
             f"Engine version: {result.get('engine_version')}",
             "Scope: simulation result; available evidence only", "Human review status: not reviewed",
             "Sources: " + json.dumps(record["sources"]), "Inputs: " + json.dumps(record["inputs"]),
             "Assumptions: " + json.dumps(record["assumptions"]),
             "Limitations: " + json.dumps(record["limitations"]),
             "Totals: " + json.dumps({key: result.get("stress", {}).get(key) for key in
                                       ("gross_revenue_inr", "cash_pre_due_inr", "due_inr", "cash_gap_inr")})]
    text_lines = [wrapped for item in lines for wrapped in textwrap.wrap(str(item), width=88) or [""]]
    stream = "BT /F1 9 Tf 42 800 Td " + " ".join(f"({pdf_escape(line)}) Tj 0 -14 Td" for line in text_lines) + " ET"
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 1200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               f"<< /Length {len(stream.encode('latin-1', 'replace'))} >>\nstream\n{stream}\nendstream".encode("latin-1", "replace")]
    pdf = bytearray(b"%PDF-1.4\n"); offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf)); pdf.extend(f"{index} 0 obj\n".encode()); pdf.extend(obj); pdf.extend(b"\nendobj\n")
    xref = len(pdf); pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]: pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return Response(bytes(pdf), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "private, no-store"})


@router.get("/farmer/reports/{assessment_id}")
def farmer_report(assessment_id: str, format: str = Query(default="json", pattern="^(json|csv|pdf)$"),
                  user: dict = Depends(get_current_user)):
    borrower_id, borrower = farmer_borrower(user)
    result = get_scenario(assessment_id)
    if result is None or result.get("borrower_id") != borrower_id:
        raise HTTPException(404, "Assessment not found")
    report = farmer_projection(borrower, result)
    report["report_scope"] = "simulation results; available evidence only"
    add_audit_event(actor_id=user["id"], actor_role=user["role"], entity_type="report",
                    entity_id=assessment_id, action=f"download_{format}", reason="Farmer downloaded own saved report",
                    result_ref=result.get("result_hash"))
    filename = f"sage-{assessment_id}.{format}"
    if format == "json":
        return Response(json.dumps(report, ensure_ascii=False, indent=2), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "private, no-store"})
    assessment = report["assessment"]
    if format == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["field", "value"])
        for key, value in assessment.items():
            writer.writerow([key, json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value])
        writer.writerow(["report_scope", report["report_scope"]])
        return Response(output.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "private, no-store"})
    pdf_text = ["Sage farmer assessment report", f"Assessment ID: {assessment['id']}",
                f"As of: {assessment['as_of']}", f"Result hash: {assessment.get('result_hash')}",
                f"Engine version: {assessment['engine_version']}", f"Crop: {assessment['crop']}",
                f"Borrower ID: {assessment['borrower_id']}",
                f"Modeled cash gap (INR): {assessment['cash_gap_inr']}",
                f"Report scope: {report['report_scope']}",
                f"Human review status: {assessment['human_review_status']}",
                "Totals:"]
    for label, totals in assessment.get("totals", {}).items():
        pdf_text.append(f"{label}: {json.dumps(totals, ensure_ascii=True)}")
    for label, value in (("Inputs", assessment.get("inputs")), ("Assumptions", assessment.get("assumptions")),
                         ("Sources and input status", assessment.get("input_data_status")),
                         ("Source versions", assessment.get("source_versions")),
                         ("Source snapshot IDs", result.get("source_snapshot_ids")),
                         ("Limitations and missing evidence", assessment.get("limitations"))):
        pdf_text.append(f"{label}: {json.dumps(value, ensure_ascii=True)}")
    lines = [wrapped for item in pdf_text for wrapped in textwrap.wrap(str(item), width=88) or [""]]
    stream = "BT /F1 9 Tf 42 800 Td " + " ".join(f"({pdf_escape(line)}) Tj 0 -14 Td" for line in lines) + " ET"
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 1200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               f"<< /Length {len(stream.encode('latin-1', 'replace'))} >>\nstream\n{stream}\nendstream".encode("latin-1", "replace")]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf)); pdf.extend(f"{index} 0 obj\n".encode()); pdf.extend(obj); pdf.extend(b"\nendobj\n")
    xref = len(pdf); pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]: pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return Response(bytes(pdf), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "private, no-store"})

