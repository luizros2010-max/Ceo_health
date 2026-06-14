"""Canonical biomarker catalog seed (English + Portuguese aliases, unit factors).

Idempotent: re-running only inserts missing biomarkers/aliases/conversions, so the
catalog can grow over time without duplicating rows.
"""
from __future__ import annotations

from sqlmodel import Session, select

from ..models import Biomarker, BiomarkerAlias, Patient, UnitConversion
from ..textnorm import normalize_alias

# Each entry:
#   slug, display_name, category, canonical_unit, ref_low, ref_high, higher_is_better,
#   aliases (EN + PT, free text — normalized on insert),
#   conversions [(from_unit, to_unit, factor, offset)] into the canonical unit.
CATALOG: list[dict] = [
    {
        "slug": "glucose_fasting", "display_name": "Glucose (Fasting)", "category": "Metabolic",
        "canonical_unit": "mg/dL", "ref_low": 70, "ref_high": 99, "higher_is_better": None,
        "aliases": ["glucose", "fasting glucose", "glucose fasting", "blood glucose",
                     "glicose", "glicemia", "glicemia de jejum", "glicose em jejum", "gli"],
        "conversions": [("mmol/L", "mg/dL", 18.0182, 0.0)],
    },
    {
        "slug": "hba1c", "display_name": "Hemoglobin A1c", "category": "Metabolic",
        "canonical_unit": "%", "ref_low": 4.0, "ref_high": 5.6, "higher_is_better": False,
        "aliases": ["hba1c", "a1c", "hemoglobin a1c", "glycated hemoglobin",
                     "hemoglobina glicada", "hemoglobina glicosilada", "hb a1c"],
        "conversions": [],
    },
    {
        "slug": "insulin_fasting", "display_name": "Insulin (Fasting)", "category": "Metabolic",
        "canonical_unit": "uIU/mL", "ref_low": 2.6, "ref_high": 24.9, "higher_is_better": None,
        "aliases": ["insulin", "fasting insulin", "insulina", "insulina de jejum"],
        "conversions": [("pmol/L", "uIU/mL", 0.1389, 0.0)],
    },
    {
        "slug": "cholesterol_total", "display_name": "Total Cholesterol", "category": "Lipids",
        "canonical_unit": "mg/dL", "ref_low": None, "ref_high": 200, "higher_is_better": False,
        "aliases": ["cholesterol", "total cholesterol", "cholesterol total",
                     "colesterol", "colesterol total"],
        "conversions": [("mmol/L", "mg/dL", 38.67, 0.0)],
    },
    {
        "slug": "ldl_cholesterol", "display_name": "LDL Cholesterol", "category": "Lipids",
        "canonical_unit": "mg/dL", "ref_low": None, "ref_high": 100, "higher_is_better": False,
        "aliases": ["ldl", "ldl cholesterol", "ldl c", "ldl colesterol",
                     "colesterol ldl", "ldl direto"],
        "conversions": [("mmol/L", "mg/dL", 38.67, 0.0)],
    },
    {
        "slug": "hdl_cholesterol", "display_name": "HDL Cholesterol", "category": "Lipids",
        "canonical_unit": "mg/dL", "ref_low": 40, "ref_high": None, "higher_is_better": True,
        "aliases": ["hdl", "hdl cholesterol", "hdl c", "colesterol hdl", "hdl colesterol"],
        "conversions": [("mmol/L", "mg/dL", 38.67, 0.0)],
    },
    {
        "slug": "triglycerides", "display_name": "Triglycerides", "category": "Lipids",
        "canonical_unit": "mg/dL", "ref_low": None, "ref_high": 150, "higher_is_better": False,
        "aliases": ["triglycerides", "triglyceride", "trig", "triglicerides",
                     "triglicerideos", "triglicerideos totais"],
        "conversions": [("mmol/L", "mg/dL", 88.57, 0.0)],
    },
    {
        "slug": "creatinine", "display_name": "Creatinine", "category": "Renal",
        "canonical_unit": "mg/dL", "ref_low": 0.6, "ref_high": 1.3, "higher_is_better": False,
        "aliases": ["creatinine", "creatinina", "creat"],
        "conversions": [("umol/L", "mg/dL", 0.011312, 0.0), ("µmol/L", "mg/dL", 0.011312, 0.0)],
    },
    {
        "slug": "egfr", "display_name": "eGFR", "category": "Renal",
        "canonical_unit": "mL/min/1.73m2", "ref_low": 90, "ref_high": None, "higher_is_better": True,
        "aliases": ["egfr", "gfr", "estimated gfr", "taxa de filtracao glomerular", "tfg"],
        "conversions": [],
    },
    {
        "slug": "urea_bun", "display_name": "Urea / BUN", "category": "Renal",
        "canonical_unit": "mg/dL", "ref_low": 7, "ref_high": 20, "higher_is_better": None,
        "aliases": ["bun", "urea", "blood urea nitrogen", "ureia", "uréia"],
        "conversions": [("mmol/L", "mg/dL", 6.006, 0.0)],
    },
    {
        "slug": "uric_acid", "display_name": "Uric Acid", "category": "Metabolic",
        "canonical_unit": "mg/dL", "ref_low": 3.4, "ref_high": 7.0, "higher_is_better": False,
        "aliases": ["uric acid", "acido urico", "ácido úrico", "urate"],
        "conversions": [("umol/L", "mg/dL", 0.0168, 0.0)],
    },
    {
        "slug": "alt", "display_name": "ALT (TGP)", "category": "Liver",
        "canonical_unit": "U/L", "ref_low": None, "ref_high": 41, "higher_is_better": False,
        "aliases": ["alt", "sgpt", "tgp", "alanine aminotransferase", "alanina aminotransferase"],
        "conversions": [],
    },
    {
        "slug": "ast", "display_name": "AST (TGO)", "category": "Liver",
        "canonical_unit": "U/L", "ref_low": None, "ref_high": 40, "higher_is_better": False,
        "aliases": ["ast", "sgot", "tgo", "aspartate aminotransferase", "aspartato aminotransferase"],
        "conversions": [],
    },
    {
        "slug": "ggt", "display_name": "GGT", "category": "Liver",
        "canonical_unit": "U/L", "ref_low": None, "ref_high": 60, "higher_is_better": False,
        "aliases": ["ggt", "gamma gt", "gamma glutamyl transferase", "gama gt", "gama glutamil transferase"],
        "conversions": [],
    },
    {
        "slug": "alkaline_phosphatase", "display_name": "Alkaline Phosphatase", "category": "Liver",
        "canonical_unit": "U/L", "ref_low": 40, "ref_high": 129, "higher_is_better": None,
        "aliases": ["alkaline phosphatase", "alp", "fosfatase alcalina"],
        "conversions": [],
    },
    {
        "slug": "bilirubin_total", "display_name": "Total Bilirubin", "category": "Liver",
        "canonical_unit": "mg/dL", "ref_low": 0.1, "ref_high": 1.2, "higher_is_better": None,
        "aliases": ["bilirubin", "total bilirubin", "bilirrubina", "bilirrubina total"],
        "conversions": [("umol/L", "mg/dL", 0.05847, 0.0)],
    },
    {
        "slug": "albumin", "display_name": "Albumin", "category": "Protein",
        "canonical_unit": "g/dL", "ref_low": 3.5, "ref_high": 5.0, "higher_is_better": None,
        "aliases": ["albumin", "albumina"],
        "conversions": [("g/L", "g/dL", 0.1, 0.0)],
    },
    {
        "slug": "tsh", "display_name": "TSH", "category": "Thyroid",
        "canonical_unit": "uIU/mL", "ref_low": 0.4, "ref_high": 4.0, "higher_is_better": None,
        "aliases": ["tsh", "thyroid stimulating hormone", "hormonio tireoestimulante", "tirotrofina"],
        "conversions": [("mIU/L", "uIU/mL", 1.0, 0.0)],
    },
    {
        "slug": "free_t4", "display_name": "Free T4", "category": "Thyroid",
        "canonical_unit": "ng/dL", "ref_low": 0.8, "ref_high": 1.8, "higher_is_better": None,
        "aliases": ["free t4", "ft4", "t4 livre", "tiroxina livre"],
        "conversions": [("pmol/L", "ng/dL", 0.0777, 0.0)],
    },
    {
        "slug": "vitamin_d", "display_name": "Vitamin D (25-OH)", "category": "Vitamins",
        "canonical_unit": "ng/mL", "ref_low": 30, "ref_high": 100, "higher_is_better": True,
        "aliases": ["vitamin d", "25 oh vitamin d", "25 hydroxyvitamin d", "vitamina d",
                     "25 oh vitamina d", "vitamina d 25 hidroxi"],
        "conversions": [("nmol/L", "ng/mL", 0.4006, 0.0)],
    },
    {
        "slug": "vitamin_b12", "display_name": "Vitamin B12", "category": "Vitamins",
        "canonical_unit": "pg/mL", "ref_low": 200, "ref_high": 900, "higher_is_better": None,
        "aliases": ["vitamin b12", "b12", "cobalamin", "vitamina b12", "cobalamina"],
        "conversions": [("pmol/L", "pg/mL", 1.355, 0.0)],
    },
    {
        "slug": "ferritin", "display_name": "Ferritin", "category": "Hematology",
        "canonical_unit": "ng/mL", "ref_low": 30, "ref_high": 400, "higher_is_better": None,
        "aliases": ["ferritin", "ferritina"],
        "conversions": [("ug/L", "ng/mL", 1.0, 0.0), ("µg/L", "ng/mL", 1.0, 0.0)],
    },
    {
        "slug": "iron", "display_name": "Iron (Serum)", "category": "Hematology",
        "canonical_unit": "ug/dL", "ref_low": 60, "ref_high": 170, "higher_is_better": None,
        "aliases": ["iron", "serum iron", "ferro", "ferro serico"],
        "conversions": [("umol/L", "ug/dL", 5.585, 0.0)],
    },
    {
        "slug": "hemoglobin", "display_name": "Hemoglobin", "category": "Hematology",
        "canonical_unit": "g/dL", "ref_low": 13.5, "ref_high": 17.5, "higher_is_better": None,
        "aliases": ["hemoglobin", "hgb", "hb", "hemoglobina"],
        "conversions": [("g/L", "g/dL", 0.1, 0.0)],
    },
    {
        "slug": "hematocrit", "display_name": "Hematocrit", "category": "Hematology",
        "canonical_unit": "%", "ref_low": 38.8, "ref_high": 50.0, "higher_is_better": None,
        "aliases": ["hematocrit", "hct", "hematocrito"],
        "conversions": [],
    },
    {
        "slug": "wbc", "display_name": "White Blood Cells", "category": "Hematology",
        "canonical_unit": "10^3/uL", "ref_low": 4.0, "ref_high": 11.0, "higher_is_better": None,
        "aliases": ["wbc", "white blood cells", "leukocytes", "leucocitos", "leucócitos",
                     "globulos brancos"],
        "conversions": [],
    },
    {
        "slug": "platelets", "display_name": "Platelets", "category": "Hematology",
        "canonical_unit": "10^3/uL", "ref_low": 150, "ref_high": 400, "higher_is_better": None,
        "aliases": ["platelets", "plt", "plaquetas"],
        "conversions": [],
    },
    {
        "slug": "crp", "display_name": "C-Reactive Protein", "category": "Inflammation",
        "canonical_unit": "mg/L", "ref_low": None, "ref_high": 3.0, "higher_is_better": False,
        "aliases": ["crp", "c reactive protein", "hs crp", "pcr", "proteina c reativa",
                     "proteina c reativa ultra sensivel"],
        "conversions": [("mg/dL", "mg/L", 10.0, 0.0)],
    },
    {
        "slug": "testosterone_total", "display_name": "Total Testosterone", "category": "Hormones",
        "canonical_unit": "ng/dL", "ref_low": 264, "ref_high": 916, "higher_is_better": None,
        "aliases": ["testosterone", "total testosterone", "testosterona", "testosterona total"],
        "conversions": [("nmol/L", "ng/dL", 28.84, 0.0)],
    },
    {
        "slug": "psa_total", "display_name": "PSA (Total)", "category": "Tumor Markers",
        "canonical_unit": "ng/mL", "ref_low": None, "ref_high": 4.0, "higher_is_better": False,
        "aliases": ["psa", "total psa", "prostate specific antigen", "psa total",
                     "antigeno prostatico especifico"],
        "conversions": [],
    },
]


def seed_default_patient(session: Session) -> Patient:
    existing = session.exec(select(Patient)).first()
    if existing:
        return existing
    patient = Patient(name="Me")
    session.add(patient)
    session.flush()
    return patient


def seed_biomarkers(session: Session) -> None:
    for entry in CATALOG:
        biomarker = session.exec(
            select(Biomarker).where(Biomarker.slug == entry["slug"])
        ).first()
        if not biomarker:
            biomarker = Biomarker(
                slug=entry["slug"],
                display_name=entry["display_name"],
                category=entry["category"],
                canonical_unit=entry["canonical_unit"],
                default_ref_low=entry["ref_low"],
                default_ref_high=entry["ref_high"],
                higher_is_better=entry["higher_is_better"],
            )
            session.add(biomarker)
            session.flush()

        # Aliases (normalized + accent-folded). Always include the display name.
        alias_sources = list(entry["aliases"]) + [entry["display_name"], entry["slug"].replace("_", " ")]
        for raw_alias in alias_sources:
            norm = normalize_alias(raw_alias)
            if not norm:
                continue
            exists = session.exec(
                select(BiomarkerAlias).where(BiomarkerAlias.alias_text == norm)
            ).first()
            if not exists:
                session.add(BiomarkerAlias(biomarker_id=biomarker.id, alias_text=norm))

        # Unit conversions into the canonical unit.
        for from_unit, to_unit, factor, offset in entry["conversions"]:
            exists = session.exec(
                select(UnitConversion).where(
                    UnitConversion.biomarker_id == biomarker.id,
                    UnitConversion.from_unit == from_unit,
                    UnitConversion.to_unit == to_unit,
                )
            ).first()
            if not exists:
                session.add(
                    UnitConversion(
                        biomarker_id=biomarker.id,
                        from_unit=from_unit,
                        to_unit=to_unit,
                        factor=factor,
                        offset=offset,
                    )
                )
