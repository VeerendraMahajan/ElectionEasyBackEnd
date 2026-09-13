import asyncio
import uuid
from typing import List
from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.repositories.job_repository import JobRepository
from app.repositories.document_repository import DocumentRepository
from app.services.extraction_service import ExtractionService
from app.core.logging import logger


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_document_job(self, job_id_str: str, document_id_strs: List[str], pdf_paths: List[str]):
    """Celery background worker task for running document extraction asynchronously."""
    job_id = uuid.UUID(job_id_str)
    document_ids = [uuid.UUID(d) for d in document_id_strs]

    async def _async_run():
        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            doc_repo = DocumentRepository(session)
            await job_repo.mark_started(job_id)

            for doc_id, pdf_path in zip(document_ids, pdf_paths):
                await doc_repo.update_status(doc_id, "PROCESSING")

                async def progress_cb(pages_delta: int, records_delta: int, failed_delta: int):
                    await job_repo.increment_progress(
                        job_id=job_id,
                        pages_delta=pages_delta,
                        records_delta=records_delta,
                        failed_records_delta=failed_delta
                    )
                    await session.commit()

                ext_service = ExtractionService(session)
                await ext_service.process_document_pages(
                    document_id=doc_id,
                    pdf_path=pdf_path,
                    progress_callback=progress_cb
                )
                await job_repo.increment_progress(job_id=job_id, docs_delta=1)
                await session.commit()

            await job_repo.mark_completed(job_id)
            await session.commit()

    try:
        asyncio.run(_async_run())
    except Exception as exc:
        logger.error(f"Celery task execution failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)
