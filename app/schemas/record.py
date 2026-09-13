import uuid
from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel, Field, ConfigDict


class VoterExtraction(BaseModel):
    """Raw / normalized extracted record from a voter region or table row."""
    serial_number: Optional[int] = Field(None, description="Serial number in electoral roll")
    house_number: Optional[str] = Field(None, description="House number as string (e.g. '1', '1ब', '15/102')")

    name_hi: Optional[str] = Field(None, description="Name in Hindi")
    name_en: Optional[str] = Field(None, description="Name in English transliteration")

    relation_type: Optional[str] = Field(None, description="'father', 'husband', 'mother', or 'other'")

    relation_name_hi: Optional[str] = Field(None, description="Relation Name in Hindi")
    relation_name_en: Optional[str] = Field(None, description="Relation Name in English transliteration")

    id_number: Optional[str] = Field(None, description="Voter ID / EPIC / SVN number (preserved exactly)")

    gender_hi: Optional[str] = Field(None, description="Gender in Hindi ('पु' / 'म' / 'अन्य')")
    gender_en: Optional[str] = Field(None, description="Gender in English ('Male' / 'Female' / 'Other')")

    age: Optional[int] = Field(None, ge=18, le=130, description="Age in years")

    photo_available: bool = Field(default=False)
    raw_record_text: Optional[str] = None
    source_bbox: Optional[Any] = None
    overall_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    validation_status: str = Field(default="VALID")
    validation_notes: List[str] = Field(default_factory=list)
    watermark: Optional[str] = Field(None, description="Watermark or status stamp e.g. 'DELETED', 'MODIFIED', 'DUPLICATE'")


class LocationInfo(BaseModel):
    assembly_number: Optional[str] = None
    assembly_name_hi: Optional[str] = None
    assembly_name_en: Optional[str] = None

    section_number: Optional[str] = None
    section_name_hi: Optional[str] = None
    section_name_en: Optional[str] = None

    part_number: Optional[str] = None

    booth_number: Optional[str] = None
    booth_name_hi: Optional[str] = None
    booth_name_en: Optional[str] = None

    booth_address_hi: Optional[str] = None
    booth_address_en: Optional[str] = None


class VoterInfo(BaseModel):
    serial_number: Optional[int] = None
    house_number: Optional[str] = None

    name_hi: Optional[str] = None
    name_en: Optional[str] = None

    relation_type: Optional[str] = None
    relation_name_hi: Optional[str] = None
    relation_name_en: Optional[str] = None

    id_number: Optional[str] = None

    gender_hi: Optional[str] = None
    gender_en: Optional[str] = None

    age: Optional[int] = None
    photo_available: Optional[bool] = False
    watermark: Optional[str] = None


class SourceInfo(BaseModel):
    document_id: Optional[uuid.UUID] = None
    page_id: Optional[uuid.UUID] = None
    page_number: Optional[int] = None
    bbox: Optional[Any] = None


class PersonRecordResponse(BaseModel):
    """Convenient nested response format matching project specification."""
    id: uuid.UUID
    location: LocationInfo
    voter: VoterInfo
    confidence: float
    validation_status: str
    watermark: Optional[str] = None
    source: SourceInfo
    created_at: datetime
    updated_at: datetime


class PersonRecordUpdate(BaseModel):
    """Schema for human review and correction (PATCH /api/v1/records/{id})."""
    serial_number: Optional[int] = None
    house_number: Optional[str] = None
    name_hi: Optional[str] = None
    name_en: Optional[str] = None
    relation_type: Optional[str] = None
    relation_name_hi: Optional[str] = None
    relation_name_en: Optional[str] = None
    id_number: Optional[str] = None
    gender_hi: Optional[str] = None
    gender_en: Optional[str] = None
    age: Optional[int] = None
    validation_status: Optional[str] = "CORRECTED"
    watermark: Optional[str] = None
    reviewer_notes: Optional[str] = None


class FieldResultResponse(BaseModel):
    id: uuid.UUID
    field_name: str
    raw_value: Optional[str] = None
    normalized_value_hi: Optional[str] = None
    normalized_value_en: Optional[str] = None
    confidence: float
    source_type: str
    source_bbox: Optional[Any] = None
    validation_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
