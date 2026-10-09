"""Filtering and KPI summaries over persisted warning evidence/task rows."""


def page_watchlist(records: list[dict], *, branch_id: str | None, status: str | None,
                   severity: str | None, page: int, page_size: int) -> dict:
    branch_options = sorted({row["branch_id"] for row in records if row.get("branch_id")})
    filtered = [row for row in records if (not branch_id or row.get("branch_id") == branch_id)
                and (not status or row["task"]["status"] == status)
                and (not severity or row.get("severity") == severity)]
    start = (page - 1) * page_size
    statuses = ("open", "assigned", "acknowledged", "resolved", "reopened", "superseded")
    return {"items": filtered[start:start + page_size], "page": page, "page_size": page_size,
        "total": len(filtered), "total_pages": (len(filtered) + page_size - 1) // page_size,
        "filters": {"branch_id": branch_id, "status": status, "severity": severity},
        "branch_options": branch_options,
        "kpis": {key: sum(row["task"]["status"] == key for row in filtered) for key in statuses},
        "security_scope_mode": "synthetic_demo_unprotected_until_f10"}
