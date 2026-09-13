import uuid
from datetime import datetime, timezone
from typing import List, TYPE_CHECKING
from sqlalchemy import String, BigInteger, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.document_page import DocumentPage
    from app.models.person_record import PersonRecord
    from app.models.processing_error import ProcessingError


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="QUEUED", index=True, nullable=False)
    total_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    pages: Mapped[List["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan", order_by="DocumentPage.page_number"
    )
    records: Mapped[List["PersonRecord"]] = relationship(
        "PersonRecord", back_populates="document", cascade="all, delete-orphan", order_by="PersonRecord.serial_number"
    )
    errors: Mapped[List["ProcessingError"]] = relationship(
        "ProcessingError", back_populates="document", cascade="all, delete-orphan"
    )
