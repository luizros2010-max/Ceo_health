"""Apple Health export importer.

Apple Health has no cloud API, so this imports the user's data export:
iPhone Health app -> profile -> "Export All Health Data" -> export.zip
(contains apple_health_export/export.xml). Pass the .zip or the .xml.

The export can be hundreds of MB, so we stream it with iterparse and aggregate
to one value per metric per day before writing observations.
"""
from __future__ import annotations

import zipfile
from collections import defaultdict
from datetime import date
from xml.etree.ElementTree import iterparse

from sqlmodel import Session

from .common import get_source, upsert_reading

SOURCE_NAME = "Apple Health"

# HK type -> (slug, unit, aggregation)  agg in {"avg","sum","latest"}
TYPES = {
    "HKQuantityTypeIdentifierRestingHeartRate": ("resting_heart_rate", "bpm", "avg"),
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": ("hrv", "ms", "avg"),
    "HKQuantityTypeIdentifierVO2Max": ("vo2max", "mL/kg/min", "latest"),
    "HKQuantityTypeIdentifierStepCount": ("steps", "steps", "sum"),
    "HKQuantityTypeIdentifierBodyMass": ("body_weight", None, "latest"),  # unit from record
    "HKQuantityTypeIdentifierOxygenSaturation": ("spo2", "%", "avg"),
    "HKQuantityTypeIdentifierBloodPressureSystolic": ("systolic_bp", "mmHg", "latest"),
    "HKQuantityTypeIdentifierBloodPressureDiastolic": ("diastolic_bp", "mmHg", "latest"),
}
SLEEP_TYPE = "HKCategoryTypeIdentifierSleepAnalysis"


def _day(s: str) -> date | None:
    try:
        return date.fromisoformat(s[:10])
    except (TypeError, ValueError):
        return None


def _open(path: str):
    if path.lower().endswith(".zip"):
        zf = zipfile.ZipFile(path)
        name = next((n for n in zf.namelist() if n.endswith("export.xml")), None)
        if not name:
            raise ValueError("No export.xml inside the zip")
        return zf.open(name)
    return open(path, "rb")


def import_apple_health(session: Session, path: str) -> dict:
    # Aggregators
    avg: dict[tuple[str, date], list[float]] = defaultdict(lambda: [0.0, 0])  # sum, count
    total: dict[tuple[str, date], float] = defaultdict(float)
    latest: dict[tuple[str, date], tuple[float, str | None]] = {}
    sleep_hours: dict[date, float] = defaultdict(float)

    fh = _open(path)
    try:
        for _event, el in iterparse(fh, events=("end",)):
            if el.tag != "Record":
                el.clear()
                continue
            rtype = el.get("type")
            day = _day(el.get("startDate") or "")
            if day is None:
                el.clear()
                continue

            if rtype == SLEEP_TYPE:
                val = (el.get("value") or "")
                if "Asleep" in val:  # AsleepCore/Deep/REM/Unspecified
                    try:
                        from datetime import datetime
                        fmt = "%Y-%m-%d %H:%M:%S %z"
                        dur = (datetime.strptime(el.get("endDate"), fmt)
                               - datetime.strptime(el.get("startDate"), fmt)).total_seconds()
                        sleep_hours[day] += dur / 3600
                    except (ValueError, TypeError):
                        pass
            elif rtype in TYPES:
                slug, unit, agg = TYPES[rtype]
                try:
                    value = float(el.get("value"))
                except (TypeError, ValueError):
                    el.clear()
                    continue
                if slug == "spo2" and value <= 1.0:
                    value *= 100
                if agg == "avg":
                    a = avg[(slug, day)]; a[0] += value; a[1] += 1
                elif agg == "sum":
                    total[(slug, day)] += value
                else:  # latest
                    latest[(slug, day)] = (value, unit or el.get("unit"))
            el.clear()
    finally:
        fh.close()

    doc = get_source(session, SOURCE_NAME)
    added = 0

    def TYPES_unit(slug):
        for _t, (sl, u, _a) in TYPES.items():
            if sl == slug:
                return u
        return None

    # avg
    for (slug, day), (ssum, cnt) in avg.items():
        if cnt:
            added += upsert_reading(session, doc, slug_or_name=slug, value=round(ssum / cnt, 2),
                                    unit=TYPES_unit(slug), day=day, extraction_method="apple_health")
    # sum
    for (slug, day), v in total.items():
        added += upsert_reading(session, doc, slug_or_name=slug, value=round(v, 1),
                                unit=TYPES_unit(slug), day=day, extraction_method="apple_health")
    # latest
    for (slug, day), (v, unit) in latest.items():
        added += upsert_reading(session, doc, slug_or_name=slug, value=v, unit=unit,
                                day=day, extraction_method="apple_health")
    # sleep
    for day, hrs in sleep_hours.items():
        if hrs > 0:
            added += upsert_reading(session, doc, slug_or_name="sleep_duration", value=round(hrs, 2),
                                    unit="h", day=day, extraction_method="apple_health")

    session.commit()
    metrics = sorted({s for (s, _d) in list(avg) + list(total) + list(latest)} | ({"sleep_duration"} if sleep_hours else set()))
    return {"ok": True, "added": added, "metrics": metrics}
