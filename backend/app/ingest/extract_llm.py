"""Claude structured extraction via forced tool-use (JSON schema).

Heterogeneous, 20-30 year, often bilingual (EN/PT) lab reports are semantic, not
regex-able. Claude is used as a *proposer*: it returns structured rows that then go
through normalize -> validate -> human review before entering the longitudinal record.

If no ANTHROPIC_API_KEY is configured, extraction is skipped gracefully and the
document is still stored (so the app is fully runnable without a key).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional

from ..config import settings

# Forced-output tool schema. Temperature 0; the model is told to emit null + notes
# rather than guess, and to copy values verbatim from the report.
EXTRACTION_TOOL = {
    "name": "record_lab_report",
    "description": "Record the structured contents of a laboratory report.",
    "input_schema": {
        "type": "object",
        "properties": {
            "lab_name": {"type": ["string", "null"]},
            "ordering_provider": {"type": ["string", "null"]},
            "collection_date": {"type": ["string", "null"], "description": "ISO date YYYY-MM-DD of sample draw"},
            "collection_date_raw": {"type": ["string", "null"]},
            "report_date": {"type": ["string", "null"], "description": "ISO date YYYY-MM-DD"},
            "report_language": {"type": ["string", "null"]},
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "raw_analyte_name": {"type": "string", "description": "Name exactly as printed"},
                        "value_raw": {"type": ["string", "null"], "description": "Value exactly as printed, e.g. '99', '<5', 'negativo'"},
                        "value_numeric": {"type": ["number", "null"]},
                        "operator": {"type": ["string", "null"], "enum": ["=", "<", ">", "<=", ">=", None]},
                        "value_qualitative": {"type": ["string", "null"]},
                        "unit_raw": {"type": ["string", "null"]},
                        "reference_low": {"type": ["number", "null"]},
                        "reference_high": {"type": ["number", "null"]},
                        "reference_raw": {"type": ["string", "null"]},
                        "flag": {"type": ["string", "null"], "description": "e.g. H, L, abnormal"},
                        "page_index": {"type": ["integer", "null"]},
                        "source_text_snippet": {"type": ["string", "null"], "description": "The line copied verbatim from the report"},
                        "confidence": {"type": "number", "description": "0..1 model confidence in this row"},
                    },
                    "required": ["raw_analyte_name"],
                },
            },
        },
        "required": ["results"],
    },
}

SYSTEM_PROMPT = (
    "You are a meticulous medical-data extraction engine. You are given the text of a "
    "laboratory report that may be in English or Portuguese and may span decades-old formats. "
    "Extract every quantitative lab result into the record_lab_report tool. Rules:\n"
    "- Copy values and units VERBATIM as printed (preserve '<5', 'negativo', decimal commas).\n"
    "- Do NOT invent or infer values. If a field is absent, use null and lower the confidence.\n"
    "- Prefer the sample COLLECTION/DRAW date for collection_date; the report/print date for report_date.\n"
    "- Put each result's verbatim source line in source_text_snippet.\n"
    "- Set confidence honestly (0..1) per row."
)


@dataclass
class ExtractedRow:
    raw_analyte_name: str
    value_raw: Optional[str] = None
    value_numeric: Optional[float] = None
    operator: Optional[str] = None
    value_qualitative: Optional[str] = None
    unit_raw: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    reference_raw: Optional[str] = None
    flag: Optional[str] = None
    page_index: Optional[int] = None
    source_text_snippet: Optional[str] = None
    confidence: float = 0.5


@dataclass
class ExtractionResult:
    ok: bool
    rows: list[ExtractedRow] = field(default_factory=list)
    lab_name: Optional[str] = None
    ordering_provider: Optional[str] = None
    collection_date: Optional[str] = None
    collection_date_raw: Optional[str] = None
    report_date: Optional[str] = None
    report_language: Optional[str] = None
    model_id: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    ms: Optional[int] = None
    error: Optional[str] = None


def extract_from_text(text: str, *, model: Optional[str] = None) -> ExtractionResult:
    if not settings.has_api_key:
        return ExtractionResult(ok=False, error="no_api_key")

    try:
        import anthropic
    except ImportError:
        return ExtractionResult(ok=False, error="anthropic_sdk_missing")

    model_id = model or settings.extract_model
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    started = time.monotonic()
    try:
        message = client.messages.create(
            model=model_id,
            max_tokens=8192,
            temperature=0,
            system=SYSTEM_PROMPT,
            tools=[EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "record_lab_report"},
            messages=[{"role": "user", "content": f"Lab report text:\n\n{text}"}],
        )
    except Exception as exc:  # network/auth/etc — keep document, surface error
        return ExtractionResult(ok=False, error=f"{type(exc).__name__}: {exc}", model_id=model_id)

    ms = int((time.monotonic() - started) * 1000)
    payload = None
    for block in message.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_lab_report":
            payload = block.input
            break
    if payload is None:
        return ExtractionResult(ok=False, error="no_tool_use_in_response", model_id=model_id, ms=ms)

    rows = [ExtractedRow(**_clean_row(r)) for r in payload.get("results", [])]
    usage = getattr(message, "usage", None)
    return ExtractionResult(
        ok=True,
        rows=rows,
        lab_name=payload.get("lab_name"),
        ordering_provider=payload.get("ordering_provider"),
        collection_date=payload.get("collection_date"),
        collection_date_raw=payload.get("collection_date_raw"),
        report_date=payload.get("report_date"),
        report_language=payload.get("report_language"),
        model_id=model_id,
        tokens_in=getattr(usage, "input_tokens", None) if usage else None,
        tokens_out=getattr(usage, "output_tokens", None) if usage else None,
        ms=ms,
    )


_ALLOWED = set(ExtractedRow.__dataclass_fields__.keys())


def _clean_row(raw: dict) -> dict:
    row = {k: v for k, v in raw.items() if k in _ALLOWED}
    if "raw_analyte_name" not in row or row["raw_analyte_name"] is None:
        row["raw_analyte_name"] = json.dumps(raw)[:120]
    if row.get("confidence") is None:
        row["confidence"] = 0.5
    return row
