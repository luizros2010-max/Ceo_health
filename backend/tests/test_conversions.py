"""Analyte-specific unit conversions against known reference values.

A wrong factor would fake a health crisis, so these are pinned to literature values.
"""
import math

from sqlmodel import select

from app.ingest.normalize import convert_value, match_biomarker, parse_reference_range
from app.models import Biomarker


def _bm(session, slug):
    return session.exec(select(Biomarker).where(Biomarker.slug == slug)).first()


def test_glucose_mmol_to_mgdl(session):
    bm = _bm(session, "glucose_fasting")
    # 5.49 mmol/L ~= 99 mg/dL (factor 18.0182).
    res = convert_value(session, bm, 5.49, "mmol/L")
    assert res.converted is True
    assert math.isclose(res.value_num, 98.92, abs_tol=0.5)
    assert res.canonical_unit == "mg/dL"


def test_cholesterol_mmol_to_mgdl(session):
    bm = _bm(session, "cholesterol_total")
    # 5.2 mmol/L ~= 201 mg/dL (factor 38.67).
    res = convert_value(session, bm, 5.2, "mmol/L")
    assert math.isclose(res.value_num, 201.08, abs_tol=0.5)


def test_creatinine_umol_to_mgdl(session):
    bm = _bm(session, "creatinine")
    # 88.4 umol/L ~= 1.0 mg/dL (factor 0.011312).
    res = convert_value(session, bm, 88.4, "umol/L")
    assert math.isclose(res.value_num, 1.0, abs_tol=0.02)


def test_same_unit_is_noop(session):
    bm = _bm(session, "glucose_fasting")
    res = convert_value(session, bm, 99.0, "mg/dL")
    assert res.value_num == 99.0
    assert res.converted is True


def test_unknown_unit_keeps_value_and_flags(session):
    bm = _bm(session, "glucose_fasting")
    res = convert_value(session, bm, 99.0, "furlongs")
    assert res.value_num == 99.0
    assert res.converted is False
    assert res.note is not None


def test_parse_reference_range():
    assert parse_reference_range("70 - 99") == (70.0, 99.0)
    assert parse_reference_range("< 200") == (None, 200.0)
    assert parse_reference_range("> 40") == (40.0, None)
    assert parse_reference_range("70 a 99") == (70.0, 99.0)


def test_exact_alias_match_english_and_portuguese(session):
    en = match_biomarker(session, "Fasting Glucose")
    pt = match_biomarker(session, "Glicemia de Jejum")
    assert en.biomarker is not None and en.biomarker.slug == "glucose_fasting"
    assert pt.biomarker is not None and pt.biomarker.slug == "glucose_fasting"
    assert en.method == "exact_alias" and en.match_confidence == 1.0


def test_fuzzy_match_handles_typo(session):
    res = match_biomarker(session, "Colesteroll Total")  # extra 'l'
    assert res.biomarker is not None
    assert res.biomarker.slug == "cholesterol_total"
    assert res.method.startswith("fuzzy")
