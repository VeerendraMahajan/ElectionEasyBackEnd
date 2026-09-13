from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.document_service import DocumentService
from app.repositories.document_repository import DocumentRepository
from app.repositories.page_repository import PageRepository
from app.repositories.record_repository import RecordRepository
from app.repositories.job_repository import JobRepository


def get_document_repository(session: AsyncSession = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(session)


def get_page_repository(session: AsyncSession = Depends(get_db)) -> PageRepository:
    return PageRepository(session)


def get_record_repository(session: AsyncSession = Depends(get_db)) -> RecordRepository:
    return RecordRepository(session)


def get_job_repository(session: AsyncSession = Depends(get_db)) -> JobRepository:
    return JobRepository(session)


def get_document_service(session: AsyncSession = Depends(get_db)) -> DocumentService:
    return DocumentService(session)
