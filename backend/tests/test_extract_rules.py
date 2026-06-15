from app.ingest.extract_rules import detect_narrative, extract_from_text

LAB = """Hospital Britanico
FECHA INGRESO MUESTRA 16/01/26
GLICEMIA BASAL 1.00 g/L 0.70 - 1.00
COLESTEROL TOTAL 217 mg/dL
LDL COLESTEROL 154.62 mg/dL
HEMOGLOBINA GLICOSILADA 4.9 %
HEMOGLOBINA 14.8 g/dL 13.0 - 17.0
"""


def _row(rows, name):
    return next((r for r in rows if r.raw_analyte_name == name), None)


def test_rules_extracts_values_and_date(session):
    res = extract_from_text(session, LAB)
    assert res.collection_date and res.collection_date.isoformat() == "2026-01-16"
    chol = _row(res.rows, "Total Cholesterol")
    assert chol and chol.value_numeric == 217
    ldl = _row(res.rows, "LDL Cholesterol")
    assert ldl and ldl.value_numeric == 154.62


def test_rules_no_hemoglobin_hba1c_overlap(session):
    res = extract_from_text(session, LAB)
    hba1c = _row(res.rows, "Hemoglobin A1c")
    hb = _row(res.rows, "Hemoglobin")
    assert hba1c and hba1c.value_numeric == 4.9
    assert hb and hb.value_numeric == 14.8   # not 4.9


def test_detect_narrative_echo():
    text = "ECOCARDIOGRAMA basal normal.\nEn suma: estudio dentro de limites normales."
    n = detect_narrative(text)
    assert n and n.category == "Cardiology"
    assert "normal" in (n.impression or "").lower()


def test_detect_narrative_none_for_plain_labs(session):
    assert detect_narrative("Glucose 99 mg/dL\nCholesterol 200 mg/dL") is None
