import uuid
from typing import Optional, List, Tuple
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document
from app.models.processing_error import ProcessingError


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, document_id: uuid.UUID) -> Optional[Document]:
        stmt = select(Document).where(Document.id == document_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_sha256(self, sha256_hash: str) -> Optional[Document]:
        stmt = select(Document).where(Document.sha256 == sha256_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        original_filename: str,
        file_type: str,
        file_size: int,
        sha256_hash: str,
        total_pages: int = 0,
        status: str = "QUEUED",
        doc_id: Optional[uuid.UUID] = None
    ) -> Document:
        doc = Document(
            id=doc_id or uuid.uuid4(),
            original_filename=original_filename,
            file_type=file_type,
            file_size=file_size,
            sha256=sha256_hash,
            total_pages=total_pages,
            status=status,
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def list(self, skip: int = 0, limit: int = 50) -> Tuple[List[Document], int]:
        total_stmt = select(func.count(Document.id))
        total = (await self.session.execute(total_stmt)).scalar() or 0

        stmt = select(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items), total

    async def update_status(self, document_id: uuid.UUID, status: str, total_pages: Optional[int] = None) -> None:
        values = {"status": status}
        if total_pages is not None:
            values["total_pages"] = total_pages
        stmt = update(Document).where(Document.id == document_id).values(**values)
        await self.session.execute(stmt)
        await self.session.flush()

    async def log_error(
        self,
        document_id: uuid.UUID,
        error_type: str,
        message: str,
        page_id: Optional[uuid.UUID] = None,
        record_id: Optional[uuid.UUID] = None,
        stack_trace: Optional[str] = None,
    ) -> ProcessingError:
        err = ProcessingError(
            document_id=document_id,
            page_id=page_id,
            record_id=record_id,
            error_type=error_type,
            message=message,
            stack_trace=stack_trace,
        )
        self.session.add(err)
        await self.session.flush()
        return err
