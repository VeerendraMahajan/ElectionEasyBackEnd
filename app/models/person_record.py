import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, Text, Boolean, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.document_page import DocumentPage
    from app.models.extraction_field import ExtractionFieldResult


class PersonRecord(Base):
    __tablename__ = "person_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )

    serial_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    house_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    name_hi: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    relation_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    relation_name_hi: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    relation_name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    id_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    gender_hi: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    gender_en: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    photo_available: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)

    raw_record_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_bbox: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    overall_confidence: Mapped[float] = mapped_column(Float, default=1.0, index=True)
    validation_status: Mapped[str] = mapped_column(String(50), default="VALID", index=True)
    watermark: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Booth / Polling Station Details for every voter
    booth_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    booth_name_hi: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    booth_name_en: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    booth_address_hi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    booth_address_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Human review audit trail
    correction_history: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

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
    document: Mapped["Document"] = relationship("Document", back_populates="records")
    page: Mapped["DocumentPage"] = relationship("DocumentPage", back_populates="records")
    field_results: Mapped[List["ExtractionFieldResult"]] = relationship(
        "ExtractionFieldResult", back_populates="person_record", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_person_doc_page_serial", "document_id", "page_id", "serial_number"),
        Index("ix_person_id_number", "id_number"),
        Index("ix_person_validation_conf", "validation_status", "overall_confidence"),
        Index("ix_person_booth_number", "booth_number"),
    )
