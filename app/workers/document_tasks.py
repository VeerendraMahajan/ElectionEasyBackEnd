import asyncio
import uuid
from typing import List, Optional
from celery.exceptions import MaxRetriesExceededError
from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.repositories.job_repository import JobRepository
from app.repositories.document_repository import DocumentRepository
from app.services.extraction_service import ExtractionService
from app.core.logging import logger


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_document_job(
    self,
    job_id_str: str,
    document_id_strs: List[str],
    pdf_paths: List[str],
    format_hint: Optional[str] = None,
):
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
                        failed_records_delta=failed_delta,
                    )
                    await session.commit()

                ext_service = ExtractionService(session)
                await ext_service.process_document_pages(
                    document_id=doc_id,
                    pdf_path=pdf_path,
                    progress_callback=progress_cb,
                    format_hint=format_hint,
                )
                await job_repo.increment_progress(job_id=job_id, docs_delta=1)
                await session.commit()

            await job_repo.mark_completed(job_id)
            await session.commit()

    async def _async_fail(err_msg: str):
        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            doc_repo = DocumentRepository(session)
            for doc_id in document_ids:
                try:
                    await doc_repo.update_status(doc_id, "FAILED")
                except Exception:
                    pass
            await job_repo.mark_failed(job_id, error_message=err_msg)
            await session.commit()

    try:
        asyncio.run(_async_run())
    except Exception as exc:
        is_last_attempt = (self.request.retries >= self.max_retries)
        logger.error(
            f"Celery task execution failed for job {job_id} (retry {self.request.retries}/{self.max_retries}): {exc}",
            exc_info=True,
        )
        if is_last_attempt:
            try:
                asyncio.run(_async_fail(str(exc)))
            except Exception as fail_err:
                logger.error(f"Failed to record job failure in database: {fail_err}")
            raise
        else:
            raise self.retry(exc=exc)
