"""Import only the explicit Pune maize subset from a local CY-Bench v1.10 ZIP."""
from __future__ import annotations

import argparse
import json

from app.db import init_db
from app.schemas import FeatureSnapshotImport
from app.services.cybench_subset import build_pune_maize_import
from app.services.feature_ingest import freeze_feature_import


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, help="Locally downloaded CY-Bench v1.10 ZIP (not extracted)")
    parser.add_argument("--crosswalk", required=True, help="Reviewed JSON adm_id to district/state mapping")
    parser.add_argument("--yield-unit", required=True, choices=("t/ha", "kg/ha"),
                        help="Unit confirmed from the inspected yield CSV/source metadata")
    args = parser.parse_args()
    payload = build_pune_maize_import(args.archive, args.crosswalk, yield_unit=args.yield_unit)
    request = FeatureSnapshotImport.model_validate(payload)
    init_db()
    record = freeze_feature_import(request)
    print(json.dumps({key: record[key] for key in (
        "snapshot_id", "quality_status", "row_count", "content_sha256", "source_file_hashes",
        "harvest_year_start", "harvest_year_end", "date_start", "date_end", "variables")}, indent=2))


if __name__ == "__main__":
    main()
