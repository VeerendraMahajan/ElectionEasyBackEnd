import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ExtractionJobResponse(BaseModel):
    id: uuid.UUID
    status: str
    total_documents: int
    processed_documents: int
    total_pages: int
    processed_pages: int
    total_records: int
    processed_records: int
    failed_records: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
