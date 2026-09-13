import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    original_filename: str
    file_type: str
    file_size: int
    sha256: str
    status: str
    total_pages: int


class DocumentResponse(DocumentBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    message: str
    documents: List[DocumentResponse]
