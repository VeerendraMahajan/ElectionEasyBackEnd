import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.person_record import PersonRecord
    from app.models.processing_error import ProcessingError


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Page-Level Electoral Hierarchy
    assembly_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    assembly_name_hi: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assembly_name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    section_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    section_name_hi: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    section_name_en: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    part_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    booth_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    booth_name_hi: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    booth_name_en: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    booth_address_hi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    booth_address_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Geometry & Source Audit Evidence
    page_width: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    page_height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    raw_header_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    header_bbox: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    header_confidence: Mapped[Optional[float]] = mapped_column(Float, default=1.0)

    extraction_method: Mapped[Optional[str]] = mapped_column(String(100), default="UNKNOWN")
    processing_status: Mapped[str] = mapped_column(String(50), default="QUEUED", index=True, nullable=False)

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
    document: Mapped["Document"] = relationship("Document", back_populates="pages")
    records: Mapped[List["PersonRecord"]] = relationship(
        "PersonRecord", back_populates="page", cascade="all, delete-orphan", order_by="PersonRecord.serial_number"
    )
    errors: Mapped[List["ProcessingError"]] = relationship(
        "ProcessingError", back_populates="page", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_doc_page_unique", "document_id", "page_number", unique=True),
        Index("ix_doc_page_hierarchy", "assembly_number", "part_number", "section_number", "booth_number"),
    )
