from datetime import date

from sqlmodel import select

from app.connectors.apple_health import import_apple_health
from app.models import Biomarker, Observation

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" unit="count/min" value="58" startDate="2026-01-10 08:00:00 -0300" endDate="2026-01-10 08:00:00 -0300"/>
 <Record type="HKQuantityTypeIdentifierStepCount" unit="count" value="3000" startDate="2026-01-10 09:00:00 -0300" endDate="2026-01-10 09:30:00 -0300"/>
 <Record type="HKQuantityTypeIdentifierStepCount" unit="count" value="4000" startDate="2026-01-10 18:00:00 -0300" endDate="2026-01-10 18:30:00 -0300"/>
 <Record type="HKQuantityTypeIdentifierVO2Max" unit="mL/min·kg" value="34" startDate="2026-01-10 07:00:00 -0300" endDate="2026-01-10 07:00:00 -0300"/>
 <Record type="HKQuantityTypeIdentifierOxygenSaturation" unit="%" value="0.97" startDate="2026-01-10 03:00:00 -0300" endDate="2026-01-10 03:00:00 -0300"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" value="HKCategoryValueSleepAnalysisAsleepCore" startDate="2026-01-10 23:00:00 -0300" endDate="2026-01-11 06:00:00 -0300"/>
</HealthData>
"""


def _val(session, slug, day):
    bm = session.exec(select(Biomarker).where(Biomarker.slug == slug)).first()
    o = session.exec(
        select(Observation).where(
            Observation.biomarker_id == bm.id, Observation.collection_date == day
        )
    ).first()
    return o.value_num if o else None


def test_apple_health_import(session, tmp_path):
    p = tmp_path / "export.xml"
    p.write_text(SAMPLE)
    res = import_apple_health(session, str(p))
    assert res["added"] > 0
    d = date(2026, 1, 10)
    assert _val(session, "resting_heart_rate", d) == 58
    assert _val(session, "steps", d) == 7000          # summed
    assert _val(session, "vo2max", d) == 34
    assert _val(session, "spo2", d) == 97             # fraction -> percent
    assert abs(_val(session, "sleep_duration", d) - 7.0) < 0.05


def test_apple_health_reimport_is_idempotent(session, tmp_path):
    p = tmp_path / "export.xml"
    p.write_text(SAMPLE)
    import_apple_health(session, str(p))
    n1 = len(session.exec(select(Observation)).all())
    import_apple_health(session, str(p))
    n2 = len(session.exec(select(Observation)).all())
    assert n1 == n2  # no duplicates on re-import
