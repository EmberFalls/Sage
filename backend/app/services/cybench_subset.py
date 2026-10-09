"""Stream a small, explicitly crosswalked CY-Bench India maize subset."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

CYBENCH_URL = "https://zenodo.org/records/17279151"
TARGET_YEAR = 2015
TARGET_DISTRICT = "pune"
TARGET_STATE = "maharashtra"


def _find_member(archive: zipfile.ZipFile, ending: str) -> str:
    matches = [name for name in archive.namelist() if name.replace("\\", "/").lower().endswith(ending)]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one CY-Bench archive member ending in {ending!r}; found {len(matches)}")
    return matches[0]


def _sha256_member(archive: zipfile.ZipFile, member: str) -> str:
    digest = hashlib.sha256()
    with archive.open(member) as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _iter_rows(archive: zipfile.ZipFile, member: str):
    with archive.open(member) as source:
        text = io.TextIOWrapper(source, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text)
        if not reader.fieldnames:
            raise ValueError(f"CY-Bench CSV {member} has no header")
        yield from reader


def _field(row: dict[str, str], names: tuple[str, ...], context: str) -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    raise ValueError(f"CY-Bench {context} row has no populated column from {', '.join(names)}")


def build_pune_maize_import(archive_path: str | Path, crosswalk_path: str | Path,
                            *, yield_unit: str) -> dict:
    """Build normalized F0 pilot rows; never guess a district ID or yield unit.

    The archive is never extracted. The supplied crosswalk must map CY-Bench
    adm_id values to named districts/states using inspected source boundaries.
    """
    if yield_unit not in {"t/ha", "kg/ha"}:
        raise ValueError("yield_unit must explicitly be t/ha or kg/ha")
    crosswalk = json.loads(Path(crosswalk_path).read_text(encoding="utf-8"))
    if not isinstance(crosswalk, dict):
        raise ValueError("Crosswalk must be a JSON object keyed by CY-Bench adm_id")
    selected = [str(admin_id) for admin_id, area in crosswalk.items()
                if isinstance(area, dict)
                and str(area.get("district", "")).strip().casefold() == TARGET_DISTRICT
                and str(area.get("state", "")).strip().casefold() == TARGET_STATE]
    if len(selected) != 1:
        raise ValueError(f"Crosswalk must resolve exactly one Pune, Maharashtra CY-Bench adm_id; found {len(selected)}")
    admin_id = selected[0]
    archive_path = Path(archive_path)
    rows: list[dict] = []
    with zipfile.ZipFile(archive_path) as archive:
        yield_member = _find_member(archive, "maize/in/yield_maize_in.csv")
        meteo_member = _find_member(archive, "maize/in/meteo_maize_in.csv")
        yield_hash = _sha256_member(archive, yield_member)
        meteo_hash = _sha256_member(archive, meteo_member)
        target_yields = [row for row in _iter_rows(archive, yield_member)
                         if str(row.get("adm_id", "")).strip() == admin_id
                         and str(row.get("harvest_year", "")).strip() == str(TARGET_YEAR)]
        if len(target_yields) != 1:
            raise ValueError(f"Expected one yield row for adm_id={admin_id}, harvest_year={TARGET_YEAR}; found {len(target_yields)}")
        source_yield = _field(target_yields[0], ("yield_t_ha", "yield_t_per_ha", "yield"), "yield")
        value = float(source_yield)
        if yield_unit == "kg/ha":
            value /= 1000
        rows.append({"variable": "yield_t_per_ha", "value": value, "unit": "t/ha",
                     "geography": "Pune, Maharashtra (explicit source-boundary crosswalk)",
                     "geography_id": admin_id, "crop": "maize", "harvest_year": TARGET_YEAR,
                     "source_member": yield_member})
        columns = {
            "rainfall_mm": ("precipitation_sum", "precipitation", "precip", "pr"),
            "tmax_c": ("temperature_2m_max", "tmax", "tmax_c", "tasmax"),
            "tmin_c": ("temperature_2m_min", "tmin", "tmin_c", "tasmin"),
        }
        found: dict[str, int] = {key: 0 for key in columns}
        for source_row in _iter_rows(archive, meteo_member):
            if str(source_row.get("adm_id", "")).strip() != admin_id:
                continue
            day = _field(source_row, ("time", "date", "day"), "weather")
            if not day.startswith("2015-") or not "2015-06-01" <= day <= "2015-10-31":
                continue
            for variable, aliases in columns.items():
                value = float(_field(source_row, aliases, "weather"))
                rows.append({"variable": variable, "value": value,
                             "unit": "mm" if variable == "rainfall_mm" else "degC",
                             "geography": "Pune, Maharashtra (explicit source-boundary crosswalk)",
                             "geography_id": admin_id, "crop": "maize", "observed_at": day,
                             "source_member": meteo_member})
                found[variable] += 1
        if not all(count > 0 for count in found.values()):
            raise ValueError(f"Weather subset missing one or more required variables: {found}")
    return {
        "source_id": "cybench", "source_url": CYBENCH_URL,
        "attribution": "CY-Bench; underlying statistical and predictor sources require separate attribution review",
        "license": "Pending archive and component-source license review; not admitted for runtime use",
        "dataset_version": "1.10", "geography": "Pune, Maharashtra; CY-Bench adm_id crosswalk required",
        "source_file_hashes": {yield_member: yield_hash, meteo_member: meteo_hash},
        "observations": rows,
    }
