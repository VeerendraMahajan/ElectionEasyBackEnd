import uuid
from datetime import datetime, timezone
from typing import Optional, Any, TYPE_CHECKING
from sqlalchemy import String, Float, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.person_record import PersonRecord


class ExtractionFieldResult(Base):
    __tablename__ = "extraction_field_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    person_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person_records.id", ondelete="CASCADE"), nullable=False, index=True
    )

    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    raw_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    normalized_value_hi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_value_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source_type: Mapped[str] = mapped_column(String(50), default="OCR")
    source_bbox: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    validation_status: Mapped[str] = mapped_column(String(50), default="VALID")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    person_record: Mapped["PersonRecord"] = relationship("PersonRecord", back_populates="field_results")

    __table_args__ = (
        Index("ix_field_record_name", "person_record_id", "field_name"),
    )
