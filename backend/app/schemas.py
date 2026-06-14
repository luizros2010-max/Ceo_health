"""API request/response DTOs."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class DocumentPatch(BaseModel):
    lab_name: Optional[str] = None
    collection_date: Optional[date] = None
    notes: Optional[str] = None


class ManualObservation(BaseModel):
    biomarker_slug: str
    value_num: float
    unit: Optional[str] = None
    collection_date: date
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    notes: Optional[str] = None


class ObservationPatch(BaseModel):
    status: Optional[str] = None  # 'confirmed' | 'rejected' | 'needs_review'
    biomarker_slug: Optional[str] = None  # re-map -> also learns a new alias
    value_num: Optional[float] = None
    collection_date: Optional[date] = None
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    learn_alias: bool = True  # when re-mapping, append raw_name as a new alias
