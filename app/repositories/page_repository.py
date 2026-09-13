import uuid
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document_page import DocumentPage
from app.schemas.page import PageHeaderExtraction


class PageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, page_id: uuid.UUID) -> Optional[DocumentPage]:
        stmt = select(DocumentPage).where(DocumentPage.id == page_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_doc_and_number(self, document_id: uuid.UUID, page_number: int) -> Optional[DocumentPage]:
        stmt = select(DocumentPage).where(
            DocumentPage.document_id == document_id,
            DocumentPage.page_number == page_number
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        document_id: uuid.UUID,
        page_number: int,
        page_width: Optional[float] = None,
        page_height: Optional[float] = None,
        processing_status: str = "QUEUED",
        extraction_method: str = "UNKNOWN",
        page_id: Optional[uuid.UUID] = None
    ) -> DocumentPage:
        page = DocumentPage(
            id=page_id or uuid.uuid4(),
            document_id=document_id,
            page_number=page_number,
            page_width=page_width,
            page_height=page_height,
            processing_status=processing_status,
            extraction_method=extraction_method,
        )
        self.session.add(page)
        await self.session.flush()
        return page

    async def update_header(self, page_id: uuid.UUID, header: PageHeaderExtraction, raw_header_text: Optional[str] = None, header_bbox: Optional[list] = None) -> None:
        values = {
            "assembly_number": header.assembly_number,
            "assembly_name_hi": header.assembly_name_hi,
            "assembly_name_en": header.assembly_name_en,
            "section_number": header.section_number,
            "section_name_hi": header.section_name_hi,
            "section_name_en": header.section_name_en,
            "part_number": header.part_number,
            "booth_number": header.booth_number,
            "booth_name_hi": header.booth_name_hi,
            "booth_name_en": header.booth_name_en,
            "booth_address_hi": header.booth_address_hi,
            "booth_address_en": header.booth_address_en,
            "header_confidence": header.confidence,
        }
        if raw_header_text is not None:
            values["raw_header_text"] = raw_header_text
        if header_bbox is not None:
            values["header_bbox"] = header_bbox

        stmt = update(DocumentPage).where(DocumentPage.id == page_id).values(**values)
        await self.session.execute(stmt)
        await self.session.flush()

    async def update_status(self, page_id: uuid.UUID, status: str, method: Optional[str] = None) -> None:
        values = {"processing_status": status}
        if method:
            values["extraction_method"] = method
        stmt = update(DocumentPage).where(DocumentPage.id == page_id).values(**values)
        await self.session.execute(stmt)
        await self.session.flush()

    async def list_by_document(self, document_id: uuid.UUID) -> List[DocumentPage]:
        stmt = (
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
