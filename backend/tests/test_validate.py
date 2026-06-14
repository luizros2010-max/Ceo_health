from datetime import date

from app.ingest.validate import compose_confidence, validate_row, value_in_source


def test_value_in_source_detects_presence():
    assert value_in_source("99", "Glucose 99 mg/dL") is True
    assert value_in_source("5,49", "Glicose 5.49 mmol/L") is True  # decimal comma/point
    assert value_in_source("123", "Glucose 99 mg/dL") is False


def test_validate_rejects_value_not_in_source():
    res = validate_row(
        value_raw="123",
        value_num=123,
        source_text_snippet="Glucose 99 mg/dL",
        full_text="Glucose 99 mg/dL",
        ref_low=70,
        ref_high=99,
        collection_date=date(2020, 1, 1),
        birth_date=date(1980, 1, 1),
        today=date(2026, 6, 14),
    )
    assert res.ok is False
    assert "value_not_in_source" in res.issues
    assert res.penalties > 0


def test_validate_flags_future_date():
    res = validate_row(
        value_raw="99",
        value_num=99,
        source_text_snippet="Glucose 99",
        full_text="Glucose 99",
        ref_low=70,
        ref_high=99,
        collection_date=date(2030, 1, 1),
        birth_date=date(1980, 1, 1),
        today=date(2026, 6, 14),
    )
    assert "collection_date_in_future" in res.issues


def test_validate_flags_date_before_birth():
    res = validate_row(
        value_raw="99",
        value_num=99,
        source_text_snippet="Glucose 99",
        full_text="Glucose 99",
        ref_low=70,
        ref_high=99,
        collection_date=date(1975, 1, 1),
        birth_date=date(1980, 1, 1),
        today=date(2026, 6, 14),
    )
    assert "collection_date_before_birth" in res.issues


def test_compose_confidence_blend_and_penalty():
    # Perfect model + exact match, no penalty -> 1.0
    assert compose_confidence(1.0, 1.0, 0.0) == 1.0
    # Penalty subtracts.
    assert compose_confidence(1.0, 1.0, 0.5) == 0.5
    # Clamped to [0,1].
    assert compose_confidence(1.0, 1.0, 2.0) == 0.0
