"""Oura Ring connector (Oura API v2).

Uses a Personal Access Token to pull daily summaries and map them to biomarkers:
- daily_sleep      -> resting_heart_rate (lowest HR), hrv (average), sleep_duration
- daily_spo2       -> spo2
- daily_activity   -> steps
- daily_cardiovascular_age / vo2max if available

The mapping is deliberately small and robust to missing fields. Network calls
require a token; see https://cloud.ouraring.com/personal-access-tokens
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlmodel import Session

from .common import get_source, upsert_reading

BASE = "https://api.ouraring.com/v2/usercollection"
SOURCE_NAME = "Oura Ring"


def _get(client, token: str, path: str, start: str, end: str):
    r = client.get(
        f"{BASE}/{path}",
        headers={"Authorization": f"Bearer {token}"},
        params={"start_date": start, "end_date": end},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def sync_oura(session: Session, token: str, days: int = 90) -> dict:
    import httpx

    end = date.today()
    start = end - timedelta(days=days)
    s, e = start.isoformat(), end.isoformat()
    doc = get_source(session, SOURCE_NAME)
    added = 0
    errors: list[str] = []

    def day_of(rec) -> date | None:
        d = rec.get("day") or rec.get("date")
        try:
            return datetime.fromisoformat(d).date() if "T" in str(d) else date.fromisoformat(d)
        except (TypeError, ValueError):
            return None

    with httpx.Client() as client:
        # Sleep: resting HR, HRV, total sleep duration
        try:
            for rec in _get(client, token, "sleep", s, e):
                day = day_of(rec)
                if not day:
                    continue
                if rec.get("lowest_heart_rate"):
                    added += upsert_reading(session, doc, slug_or_name="resting_heart_rate",
                                            value=rec["lowest_heart_rate"], unit="bpm", day=day,
                                            extraction_method="oura")
                if rec.get("average_hrv"):
                    added += upsert_reading(session, doc, slug_or_name="hrv",
                                            value=rec["average_hrv"], unit="ms", day=day,
                                            extraction_method="oura")
                if rec.get("total_sleep_duration"):
                    added += upsert_reading(session, doc, slug_or_name="sleep_duration",
                                            value=round(rec["total_sleep_duration"] / 3600, 2),
                                            unit="h", day=day, extraction_method="oura")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"sleep: {exc}")

        # SpO2
        try:
            for rec in _get(client, token, "daily_spo2", s, e):
                day = day_of(rec)
                pct = (rec.get("spo2_percentage") or {}).get("average") if isinstance(rec.get("spo2_percentage"), dict) else rec.get("spo2_percentage")
                if day and pct:
                    added += upsert_reading(session, doc, slug_or_name="spo2", value=pct,
                                            unit="%", day=day, extraction_method="oura")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"spo2: {exc}")

        # Activity: steps
        try:
            for rec in _get(client, token, "daily_activity", s, e):
                day = day_of(rec)
                if day and rec.get("steps"):
                    added += upsert_reading(session, doc, slug_or_name="steps", value=rec["steps"],
                                            unit="steps", day=day, extraction_method="oura")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"activity: {exc}")

    session.commit()
    return {"ok": not errors or added > 0, "added": added, "errors": errors,
            "range": {"from": s, "to": e}}
