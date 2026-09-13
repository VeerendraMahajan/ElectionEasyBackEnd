import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, func, update, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.person_record import PersonRecord
from app.models.document_page import DocumentPage
from app.models.extraction_field import ExtractionFieldResult
from app.schemas.record import VoterExtraction, PersonRecordUpdate


class RecordRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, record_id: uuid.UUID) -> Optional[PersonRecord]:
        stmt = (
            select(PersonRecord)
            .options(selectinload(PersonRecord.page), selectinload(PersonRecord.field_results))
            .where(PersonRecord.id == record_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_batch(
        self,
        document_id: uuid.UUID,
        page_id: uuid.UUID,
        voters: List[VoterExtraction]
    ) -> List[PersonRecord]:
        records: List[PersonRecord] = []
        for v in voters:
            record_id = uuid.uuid4()
            record = PersonRecord(
                id=record_id,
                document_id=document_id,
                page_id=page_id,
                serial_number=v.serial_number,
                house_number=v.house_number,
                name_hi=v.name_hi,
                name_en=v.name_en,
                relation_type=v.relation_type,
                relation_name_hi=v.relation_name_hi,
                relation_name_en=v.relation_name_en,
                id_number=v.id_number,
                gender_hi=v.gender_hi,
                gender_en=v.gender_en,
                age=v.age,
                photo_available=v.photo_available,
                raw_record_text=v.raw_record_text,
                source_bbox=v.source_bbox,
                overall_confidence=v.overall_confidence,
                validation_status=v.validation_status,
                watermark=v.watermark,
            )
            records.append(record)
            self.session.add(record)

            # Also create field results for auditability
            field_mappings = [
                ("name", v.name_hi, v.name_hi, v.name_en),
                ("relation_name", v.relation_name_hi, v.relation_name_hi, v.relation_name_en),
                ("id_number", v.id_number, v.id_number, v.id_number),
                ("house_number", v.house_number, v.house_number, v.house_number),
                ("gender", v.gender_hi, v.gender_hi, v.gender_en),
                ("age", str(v.age) if v.age is not None else None, str(v.age) if v.age is not None else None, str(v.age) if v.age is not None else None),
            ]
            for fname, raw_val, norm_hi, norm_en in field_mappings:
                if raw_val is not None:
                    fr = ExtractionFieldResult(
                        person_record_id=record_id,
                        field_name=fname,
                        raw_value=raw_val,
                        normalized_value_hi=norm_hi,
                        normalized_value_en=norm_en,
                        confidence=v.overall_confidence,
                        source_type="OCR",
                        validation_status=v.validation_status,
                    )
                    self.session.add(fr)

        await self.session.flush()
        return records

    async def search(
        self,
        document_id: Optional[uuid.UUID] = None,
        page_id: Optional[uuid.UUID] = None,
        page_number: Optional[int] = None,
        assembly_number: Optional[str] = None,
        section_number: Optional[str] = None,
        part_number: Optional[str] = None,
        booth_number: Optional[str] = None,
        gender: Optional[str] = None,
        id_number: Optional[str] = None,
        house_number: Optional[str] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        validation_status: Optional[str] = None,
        min_confidence: Optional[float] = None,
        sort_by: str = "serial_number",
        sort_order: str = "asc",
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PersonRecord], int]:
        stmt = (
            select(PersonRecord)
            .join(DocumentPage, PersonRecord.page_id == DocumentPage.id)
            .options(selectinload(PersonRecord.page))
        )
        count_stmt = select(func.count(PersonRecord.id)).join(DocumentPage, PersonRecord.page_id == DocumentPage.id)

        filters = []
        if document_id:
            filters.append(PersonRecord.document_id == document_id)
        if page_id:
            filters.append(PersonRecord.page_id == page_id)
        if page_number:
            filters.append(DocumentPage.page_number == page_number)
        if assembly_number:
            filters.append(DocumentPage.assembly_number == assembly_number)
        if section_number:
            filters.append(DocumentPage.section_number == section_number)
        if part_number:
            filters.append(DocumentPage.part_number == part_number)
        if booth_number:
            filters.append(DocumentPage.booth_number == booth_number)
        if gender:
            filters.append(
                (PersonRecord.gender_en.ilike(f"%{gender}%")) | (PersonRecord.gender_hi == gender)
            )
        if id_number:
            filters.append(PersonRecord.id_number.ilike(f"%{id_number}%"))
        if house_number:
            filters.append(PersonRecord.house_number == house_number)
        if min_age is not None:
            filters.append(PersonRecord.age >= min_age)
        if max_age is not None:
            filters.append(PersonRecord.age <= max_age)
        if validation_status:
            filters.append(PersonRecord.validation_status == validation_status)
        if min_confidence is not None:
            filters.append(PersonRecord.overall_confidence >= min_confidence)

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        total = (await self.session.execute(count_stmt)).scalar() or 0

        # Sort in strict ascending order by serial number by default (1, 2, 3...)
        is_asc = sort_order.lower() == "asc"
        if sort_by == "serial_number":
            order_col = PersonRecord.serial_number.asc().nulls_last() if is_asc else PersonRecord.serial_number.desc().nulls_last()
            stmt = stmt.order_by(order_col, DocumentPage.page_number.asc())
        elif sort_by == "age":
            order_col = PersonRecord.age.asc().nulls_last() if is_asc else PersonRecord.age.desc().nulls_last()
            stmt = stmt.order_by(order_col, PersonRecord.serial_number.asc().nulls_last())
        elif sort_by == "name":
            order_col = PersonRecord.name_hi.asc().nulls_last() if is_asc else PersonRecord.name_hi.desc().nulls_last()
            stmt = stmt.order_by(order_col, PersonRecord.serial_number.asc().nulls_last())
        else:
            stmt = stmt.order_by(PersonRecord.serial_number.asc().nulls_last(), DocumentPage.page_number.asc())

        stmt = stmt.offset(skip).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items), total

    async def get_review_required(self, skip: int = 0, limit: int = 50) -> Tuple[List[PersonRecord], int]:
        return await self.search(validation_status="REVIEW_REQUIRED", skip=skip, limit=limit)

    async def update_record(self, record_id: uuid.UUID, update_data: PersonRecordUpdate) -> Optional[PersonRecord]:
        record = await self.get_by_id(record_id)
        if not record:
            return None

        # Build audit history snapshot before updating
        history_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_values": {
                "serial_number": record.serial_number,
                "house_number": record.house_number,
                "name_hi": record.name_hi,
                "name_en": record.name_en,
                "relation_type": record.relation_type,
                "relation_name_hi": record.relation_name_hi,
                "relation_name_en": record.relation_name_en,
                "id_number": record.id_number,
                "gender_hi": record.gender_hi,
                "gender_en": record.gender_en,
                "age": record.age,
                "validation_status": record.validation_status,
                "watermark": record.watermark,
            },
            "notes": update_data.reviewer_notes
        }

        current_history = record.correction_history or []
        current_history.append(history_entry)
        record.correction_history = current_history

        # Apply updates
        for field in ["serial_number", "house_number", "name_hi", "name_en", "relation_type", "relation_name_hi", "relation_name_en", "id_number", "gender_hi", "gender_en", "age", "validation_status", "watermark"]:
            val = getattr(update_data, field)
            if val is not None:
                setattr(record, field, val)

        await self.session.flush()
        return record
