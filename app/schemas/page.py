import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class PageHeaderExtraction(BaseModel):
    """Structured output schema for page-level electoral header extraction."""
    assembly_number: Optional[str] = Field(None, description="Assembly Constituency Number e.g. '214'")
    assembly_name_hi: Optional[str] = Field(None, description="Assembly Name in Hindi e.g. 'आर्य नगर'")
    assembly_name_en: Optional[str] = Field(None, description="Assembly Name in English transliteration e.g. 'Arya Nagar'")

    section_number: Optional[str] = Field(None, description="Section Number e.g. '1'")
    section_name_hi: Optional[str] = Field(None, description="Section Name in Hindi")
    section_name_en: Optional[str] = Field(None, description="Section Name in English transliteration")

    part_number: Optional[str] = Field(None, description="Part Number e.g. '15'")

    booth_number: Optional[str] = Field(None, description="Polling Station / Booth Number e.g. '001'")
    booth_name_hi: Optional[str] = Field(None, description="Booth Name in Hindi")
    booth_name_en: Optional[str] = Field(None, description="Booth Name in English transliteration")

    booth_address_hi: Optional[str] = Field(None, description="Booth Address in Hindi")
    booth_address_en: Optional[str] = Field(None, description="Booth Address in English transliteration")

    page_number: int = Field(..., description="Actual PDF page number")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PageResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    page_number: int

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

    page_width: Optional[float] = None
    page_height: Optional[float] = None

    raw_header_text: Optional[str] = None
    header_bbox: Optional[Any] = None
    header_confidence: Optional[float] = 1.0

    extraction_method: Optional[str] = "UNKNOWN"
    processing_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
