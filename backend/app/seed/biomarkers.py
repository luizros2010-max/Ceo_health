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
                     "glicose", "glicemia", "glicemia de jejum", "glicose em jejum", "gli",
                     "glicemia basal", "glucosa", "glucemia"],
        "conversions": [("mmol/L", "mg/dL", 18.0182, 0.0), ("g/L", "mg/dL", 100.0, 0.0)],
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
                     "triglicerideos", "triglicerideos totais", "trigliceridos"],
        "conversions": [("mmol/L", "mg/dL", 88.57, 0.0)],
    },
    {
        "slug": "vldl_cholesterol", "display_name": "VLDL Cholesterol", "category": "Lipids",
        "canonical_unit": "mg/dL", "ref_low": None, "ref_high": 30, "higher_is_better": False,
        "aliases": ["vldl", "vldl cholesterol", "vldl c", "vldl cholesterol calc",
                     "vldl calc", "colesterol vldl", "vldl colesterol"],
        "conversions": [("mmol/L", "mg/dL", 38.67, 0.0)],
    },
    {
        "slug": "chol_hdl_ratio", "display_name": "Cholesterol / HDL Ratio", "category": "Lipids",
        "canonical_unit": "ratio", "ref_low": None, "ref_high": 5.0, "higher_is_better": False,
        "aliases": ["risk ratio chol hdl", "cholesterol hdl ratio", "chol hdl ratio",
                     "risk ratio cholesterol hdl", "relacao colesterol hdl",
                     "indice de castelli", "chol hdl", "indice aterogenico",
                     "indice aterogenico castelli"],
        "conversions": [],
    },
    {
        "slug": "creatinine", "display_name": "Creatinine", "category": "Renal",
        "canonical_unit": "mg/dL", "ref_low": 0.6, "ref_high": 1.3, "higher_is_better": False,
        "aliases": ["creatinine", "creatinina", "creat", "creatininemia"],
        "conversions": [("umol/L", "mg/dL", 0.011312, 0.0), ("µmol/L", "mg/dL", 0.011312, 0.0)],
    },
    {
        "slug": "egfr", "display_name": "eGFR", "category": "Renal",
        "canonical_unit": "mL/min/1.73m2", "ref_low": 90, "ref_high": None, "higher_is_better": True,
        "aliases": ["egfr", "gfr", "estimated gfr", "taxa de filtracao glomerular", "tfg",
                     "filtrado glomerular", "filtrado glomerular calculado"],
        "conversions": [],
    },
    {
        "slug": "bun", "display_name": "BUN (Urea Nitrogen)", "category": "Renal",
        "canonical_unit": "mg/dL", "ref_low": 7, "ref_high": 20, "higher_is_better": None,
        "aliases": ["bun", "blood urea nitrogen", "urea nitrogen"],
        "conversions": [("mmol/L", "mg/dL", 2.801, 0.0)],
    },
    {
        "slug": "urea", "display_name": "Urea (Serum)", "category": "Renal",
        "canonical_unit": "mg/dL", "ref_low": 10, "ref_high": 50, "higher_is_better": None,
        "aliases": ["urea", "ureia", "uréia", "azoemia", "azotemia", "uremia"],
        "conversions": [("mmol/L", "mg/dL", 6.006, 0.0), ("g/L", "mg/dL", 100.0, 0.0)],
    },
    {
        "slug": "sodium", "display_name": "Sodium", "category": "Electrolytes",
        "canonical_unit": "mEq/L", "ref_low": 135, "ref_high": 145, "higher_is_better": None,
        "aliases": ["sodium", "sodio", "sódio", "na", "natremia"],
        "conversions": [("mmol/L", "mEq/L", 1.0, 0.0)],
    },
    {
        "slug": "potassium", "display_name": "Potassium", "category": "Electrolytes",
        "canonical_unit": "mEq/L", "ref_low": 3.5, "ref_high": 5.1, "higher_is_better": None,
        "aliases": ["potassium", "potasio", "potassio", "potássio", "kalemia"],
        "conversions": [("mmol/L", "mEq/L", 1.0, 0.0)],
    },
    {
        "slug": "chloride", "display_name": "Chloride", "category": "Electrolytes",
        "canonical_unit": "mEq/L", "ref_low": 98, "ref_high": 107, "higher_is_better": None,
        "aliases": ["chloride", "cloro", "cloreto", "cloremia"],
        "conversions": [("mmol/L", "mEq/L", 1.0, 0.0)],
    },
    {
        "slug": "total_protein", "display_name": "Total Protein", "category": "Protein",
        "canonical_unit": "g/dL", "ref_low": 6.3, "ref_high": 7.9, "higher_is_better": None,
        "aliases": ["total protein", "proteinas totales", "proteinas totais",
                     "proteina total", "proteínas totais", "proteinas totales sericas"],
        "conversions": [("g/L", "g/dL", 0.1, 0.0)],
    },
    {
        "slug": "uric_acid", "display_name": "Uric Acid", "category": "Metabolic",
        "canonical_unit": "mg/dL", "ref_low": 3.4, "ref_high": 7.0, "higher_is_better": False,
        "aliases": ["uric acid", "acido urico", "ácido úrico", "urate", "uricemia"],
        "conversions": [("umol/L", "mg/dL", 0.0168, 0.0)],
    },
    {
        "slug": "alt", "display_name": "ALT (TGP)", "category": "Liver",
        "canonical_unit": "U/L", "ref_low": None, "ref_high": 41, "higher_is_better": False,
        "aliases": ["alt", "sgpt", "tgp", "alanine aminotransferase", "alanina aminotransferase",
                     "gpt", "gpt alt"],
        "conversions": [],
    },
    {
        "slug": "ast", "display_name": "AST (TGO)", "category": "Liver",
        "canonical_unit": "U/L", "ref_low": None, "ref_high": 40, "higher_is_better": False,
        "aliases": ["ast", "sgot", "tgo", "aspartate aminotransferase", "aspartato aminotransferase",
                     "got", "got ast"],
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
        "aliases": ["alkaline phosphatase", "alp", "fosfatase alcalina", "fosfatasa alcalina",
                     "fosfatasas alcalinas"],
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
        "aliases": ["albumin", "albumina", "albuminemia"],
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
                     "proteina c reativa ultra sensivel", "proteina c reactiva"],
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
                     "antigeno prostatico especifico", "antigeno prostatico total",
                     "antigeno prostatico"],
        "conversions": [],
    },
    {
        "slug": "systolic_bp", "display_name": "Systolic Blood Pressure", "category": "Vitals",
        "canonical_unit": "mmHg", "ref_low": None, "ref_high": 120, "higher_is_better": False,
        "aliases": ["systolic", "systolic blood pressure", "sbp", "presion sistolica",
                     "pressao sistolica", "pas"],
        "conversions": [],
    },
    {
        "slug": "diastolic_bp", "display_name": "Diastolic Blood Pressure", "category": "Vitals",
        "canonical_unit": "mmHg", "ref_low": None, "ref_high": 80, "higher_is_better": False,
        "aliases": ["diastolic", "diastolic blood pressure", "dbp", "presion diastolica",
                     "pressao diastolica", "pad"],
        "conversions": [],
    },
    {
        "slug": "bmi", "display_name": "BMI", "category": "Body",
        "canonical_unit": "kg/m2", "ref_low": 18.5, "ref_high": 24.9, "higher_is_better": None,
        "aliases": ["bmi", "body mass index", "imc", "indice de masa corporal",
                     "indice de massa corporal"],
        "conversions": [],
    },
    {
        "slug": "waist_circumference", "display_name": "Waist Circumference", "category": "Body",
        "canonical_unit": "cm", "ref_low": None, "ref_high": 94, "higher_is_better": False,
        "aliases": ["waist", "waist circumference", "cintura", "perimetro abdominal",
                     "circunferencia abdominal", "circunferencia de cintura"],
        "conversions": [("in", "cm", 2.54, 0.0), ("inch", "cm", 2.54, 0.0)],
    },
    {
        "slug": "body_weight", "display_name": "Body Weight", "category": "Body",
        "canonical_unit": "kg", "ref_low": None, "ref_high": None, "higher_is_better": None,
        "aliases": ["weight", "body weight", "peso", "peso corporal"],
        "conversions": [("lb", "kg", 0.453592, 0.0), ("lbs", "kg", 0.453592, 0.0)],
    },
    # Wearables (Oura, Apple Health)
    {
        "slug": "resting_heart_rate", "display_name": "Resting Heart Rate", "category": "Fitness",
        "canonical_unit": "bpm", "ref_low": 40, "ref_high": 70, "higher_is_better": False,
        "aliases": ["resting heart rate", "rhr", "resting hr", "frecuencia cardiaca en reposo",
                     "lowest heart rate"],
        "conversions": [],
    },
    {
        "slug": "hrv", "display_name": "Heart Rate Variability", "category": "Fitness",
        "canonical_unit": "ms", "ref_low": None, "ref_high": None, "higher_is_better": True,
        "aliases": ["hrv", "heart rate variability", "rmssd", "sdnn", "average hrv"],
        "conversions": [],
    },
    {
        "slug": "vo2max", "display_name": "VO2 Max", "category": "Fitness",
        "canonical_unit": "mL/kg/min", "ref_low": None, "ref_high": None, "higher_is_better": True,
        "aliases": ["vo2max", "vo2 max", "cardio fitness", "vo2"],
        "conversions": [],
    },
    {
        "slug": "sleep_duration", "display_name": "Sleep Duration", "category": "Fitness",
        "canonical_unit": "h", "ref_low": 7, "ref_high": 9, "higher_is_better": None,
        "aliases": ["sleep duration", "total sleep", "time asleep", "sleep", "horas de sueno"],
        "conversions": [],
    },
    {
        "slug": "spo2", "display_name": "Blood Oxygen (SpO2)", "category": "Fitness",
        "canonical_unit": "%", "ref_low": 95, "ref_high": 100, "higher_is_better": True,
        "aliases": ["spo2", "blood oxygen", "oxygen saturation", "saturacion de oxigeno"],
        "conversions": [],
    },
    {
        "slug": "steps", "display_name": "Daily Steps", "category": "Fitness",
        "canonical_unit": "steps", "ref_low": None, "ref_high": None, "higher_is_better": True,
        "aliases": ["steps", "step count", "daily steps", "pasos"],
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
