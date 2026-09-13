import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.extraction_job import ExtractionJob


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, job_id: uuid.UUID) -> Optional[ExtractionJob]:
        stmt = select(ExtractionJob).where(ExtractionJob.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        total_documents: int = 1,
        total_pages: int = 0,
        job_id: Optional[uuid.UUID] = None
    ) -> ExtractionJob:
        job = ExtractionJob(
            id=job_id or uuid.uuid4(),
            status="QUEUED",
            total_documents=total_documents,
            processed_documents=0,
            total_pages=total_pages,
            processed_pages=0,
            total_records=0,
            processed_records=0,
            failed_records=0,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def mark_started(self, job_id: uuid.UUID, total_pages: Optional[int] = None) -> None:
        values = {
            "status": "PROCESSING",
            "started_at": datetime.now(timezone.utc),
        }
        if total_pages is not None:
            values["total_pages"] = total_pages
        stmt = update(ExtractionJob).where(ExtractionJob.id == job_id).values(**values)
        await self.session.execute(stmt)
        await self.session.flush()

    async def increment_progress(
        self,
        job_id: uuid.UUID,
        pages_delta: int = 0,
        records_delta: int = 0,
        failed_records_delta: int = 0,
        docs_delta: int = 0
    ) -> None:
        job = await self.get_by_id(job_id)
        if job:
            job.processed_pages += pages_delta
            job.processed_records += records_delta
            job.failed_records += failed_records_delta
            job.processed_documents += docs_delta
            await self.session.flush()

    async def mark_completed(self, job_id: uuid.UUID, total_records: Optional[int] = None) -> None:
        values = {
            "status": "COMPLETED",
            "completed_at": datetime.now(timezone.utc),
        }
        if total_records is not None:
            values["total_records"] = total_records
        stmt = update(ExtractionJob).where(ExtractionJob.id == job_id).values(**values)
        await self.session.execute(stmt)
        await self.session.flush()

    async def mark_failed(self, job_id: uuid.UUID, error_message: str) -> None:
        values = {
            "status": "FAILED",
            "completed_at": datetime.now(timezone.utc),
            "error_message": error_message,
        }
        stmt = update(ExtractionJob).where(ExtractionJob.id == job_id).values(**values)
        await self.session.execute(stmt)
        await self.session.flush()
