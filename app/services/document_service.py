import os
import uuid
import asyncio
from typing import List, Tuple, Optional
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import sanitize_filename, validate_file_header, validate_file_size
from app.core.exceptions import FileValidationError
from app.utils.hashing import calculate_sha256
from app.utils.file_utils import storage
from app.repositories.document_repository import DocumentRepository
from app.repositories.job_repository import JobRepository
from app.repositories.page_repository import PageRepository
from app.repositories.record_repository import RecordRepository
from app.services.zip_service import ZipService
from app.services.pdf_service import PDFService
from app.services.extraction_service import ExtractionService
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.models.document import Document
from app.core.logging import logger


class DocumentService:
    """Service to coordinate document uploads, idempotency, storage, and job scheduling."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.job_repo = JobRepository(session)

    async def handle_upload(
        self,
        upload_file: UploadFile,
        format_hint: Optional[str] = None
    ) -> DocumentUploadResponse:
        """
        Handle single PDF or ZIP upload.
        Validates magic bytes, enforces security limits, creates document & job records,
        and triggers background processing.
        """
        filename = sanitize_filename(upload_file.filename or "upload")
        content = await upload_file.read()
        file_size = len(content)

        # 1. Header & Magic Bytes Validation
        file_type = validate_file_header(content)
        validate_file_size(file_size, is_zip=(file_type == "zip"))

        # Save upload to temporary storage
        upload_rel_path = f"raw/{uuid.uuid4()}_{filename}"
        await upload_file.seek(0)
        saved_path = await storage.save_file(upload_file.file, upload_rel_path)

        # 2. Extract PDFs (if ZIP) or use single file
        pdf_paths: List[str] = []
        if file_type == "zip":
            extract_dir = os.path.join(os.path.dirname(saved_path), f"extracted_{uuid.uuid4()}")
            pdf_paths = ZipService.process_zip(saved_path, extract_dir)
        else:
            pdf_paths = [saved_path]

        # 3. Create Extraction Job
        job = await self.job_repo.create(total_documents=len(pdf_paths))

        document_responses: List[DocumentResponse] = []

        for pdf_path in pdf_paths:
            pdf_name = os.path.basename(pdf_path)
            pdf_size = os.path.getsize(pdf_path)
            sha256_hash = calculate_sha256(pdf_path)

            # Idempotency Check
            existing_doc = await self.doc_repo.get_by_sha256(sha256_hash)
            if existing_doc:
                logger.info(f"Idempotent upload: Found existing document with SHA256: {sha256_hash}")
                document_responses.append(DocumentResponse.model_validate(existing_doc))
                continue

            # Inspect PDF to count pages
            pdf_meta = PDFService.inspect_pdf(pdf_path)
            doc_record = await self.doc_repo.create(
                original_filename=pdf_name,
                file_type="pdf",
                file_size=pdf_size,
                sha256_hash=sha256_hash,
                total_pages=pdf_meta["page_count"],
                status="QUEUED"
            )
            document_responses.append(DocumentResponse.model_validate(doc_record))

        # Commit initial upload records
        await self.session.commit()

        # 4. Asynchronous Task Dispatch
        # Launch background task for document processing
        asyncio.create_task(self._run_extraction_task(job.id, [d.id for d in document_responses], pdf_paths, format_hint=format_hint))

        return DocumentUploadResponse(
            job_id=job.id,
            status="QUEUED",
            message=f"Successfully queued {len(pdf_paths)} document(s) for extraction.",
            documents=document_responses
        )

    async def _run_extraction_task(
        self,
        job_id: uuid.UUID,
        document_ids: List[uuid.UUID],
        pdf_paths: List[str],
        format_hint: Optional[str] = None
    ) -> None:
        """Background asynchronous processing worker task."""
        from app.core.database import AsyncSessionLocal
        logger.info(f"Starting background extraction task for job {job_id}")

        async with AsyncSessionLocal() as session:
            try:
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
                        progress_callback=progress_cb,
                        format_hint=format_hint
                    )
                    await job_repo.increment_progress(job_id=job_id, docs_delta=1)
                    await session.commit()

                await job_repo.mark_completed(job_id)
                await session.commit()
                logger.info(f"Job {job_id} successfully completed.")

            except Exception as e:
                logger.error(f"Job {job_id} failed: {e}", exc_info=True)
                await session.rollback()
                job_repo = JobRepository(session)
                await job_repo.mark_failed(job_id, error_message=str(e))
                await session.commit()
