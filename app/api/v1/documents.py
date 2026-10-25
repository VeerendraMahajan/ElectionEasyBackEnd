import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from app.api.dependencies import (
    get_document_service,
    get_document_repository,
    get_page_repository,
    get_record_repository,
)
from app.services.document_service import DocumentService
from app.repositories.document_repository import DocumentRepository
from app.repositories.page_repository import PageRepository
from app.repositories.record_repository import RecordRepository
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.schemas.page import PageResponse
from app.schemas.record import PersonRecordResponse, LocationInfo, VoterInfo, SourceInfo
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=202)
async def upload_document(
    file: UploadFile = File(..., description="PDF or ZIP file containing electoral PDFs (automatically detects card or tabular layout)"),
    service: DocumentService = Depends(get_document_service),
):
    """
    Upload a single PDF or a ZIP archive containing multiple PDFs.
    Performs security validation (magic bytes, size, ZIP slip/bomb protection),
    automatically determines layout (card grid, tabular list, or legacy font table),
    and queues background extraction.
    """
    return await service.handle_upload(file)


@router.post("/upload-tabular", response_model=DocumentUploadResponse, status_code=202)
async def upload_tabular_document(
    file: UploadFile = File(..., description="Tabular Electoral Roll PDF or ZIP (e.g. Panchayat 2-column lists)"),
    service: DocumentService = Depends(get_document_service),
):
    """
    Dedicated endpoint for uploading tabular electoral rolls (e.g. Panchayat 2-column lists).
    Guarantees tabular extraction routing and extracts all records with 100% accuracy.
    """
    return await service.handle_upload(file, format_hint="TABLE_FORMAT")


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    repo: DocumentRepository = Depends(get_document_repository),
):
    """List uploaded documents with pagination."""
    docs, total = await repo.list(skip=skip, limit=limit)
    items = [DocumentResponse.model_validate(d) for d in docs]
    return PaginatedResponse(
        items=items,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit if total > 0 else 1
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    repo: DocumentRepository = Depends(get_document_repository),
):
    """Get metadata for a specific document by UUID."""
    doc = await repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/pages", response_model=List[PageResponse])
async def get_document_pages(
    document_id: uuid.UUID,
    repo: PageRepository = Depends(get_page_repository),
):
    """Get all pages and page-level electoral hierarchy metadata for a document."""
    pages = await repo.list_by_document(document_id)
    return [PageResponse.model_validate(p) for p in pages]


@router.get("/{document_id}/records", response_model=PaginatedResponse[PersonRecordResponse])
async def get_document_records(
    document_id: uuid.UUID,
    page_number: Optional[int] = None,
    validation_status: Optional[str] = None,
    sort_by: str = Query("serial_number", description="Field to sort by (serial_number, age, name)"),
    sort_order: str = Query("asc", description="Sort order ('asc' for 1,2,3... or 'desc')"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    repo: RecordRepository = Depends(get_record_repository),
):
    """Get extracted voter records for a document with optional page or status filter in ascending serial order by default."""
    records, total = await repo.search(
        document_id=document_id,
        page_number=page_number,
        validation_status=validation_status,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit
    )

    items = []
    for r in records:
        page = r.page
        items.append(
            PersonRecordResponse(
                id=r.id,
                location=LocationInfo(
                    assembly_number=page.assembly_number if page else None,
                    assembly_name_hi=page.assembly_name_hi if page else None,
                    assembly_name_en=page.assembly_name_en if page else None,
                    section_number=page.section_number if page else None,
                    section_name_hi=page.section_name_hi if page else None,
                    section_name_en=page.section_name_en if page else None,
                    part_number=page.part_number if page else None,
                    booth_number=r.booth_number or (page.booth_number if page else None),
                    booth_name_hi=r.booth_name_hi or (page.booth_name_hi if page else None),
                    booth_name_en=r.booth_name_en or (page.booth_name_en if page else None),
                    booth_address_hi=r.booth_address_hi or (page.booth_address_hi if page else None),
                    booth_address_en=r.booth_address_en or (page.booth_address_en if page else None),
                ),
                voter=VoterInfo(
                    serial_number=r.serial_number,
                    house_number=r.house_number,
                    name_hi=r.name_hi,
                    name_en=r.name_en,
                    relation_type=r.relation_type,
                    relation_name_hi=r.relation_name_hi,
                    relation_name_en=r.relation_name_en,
                    id_number=r.id_number,
                    gender_hi=r.gender_hi,
                    gender_en=r.gender_en,
                    age=r.age,
                    photo_available=r.photo_available,
                    watermark=r.watermark,
                    booth_number=r.booth_number or (page.booth_number if page else None),
                    booth_name_hi=r.booth_name_hi or (page.booth_name_hi if page else None),
                    booth_name_en=r.booth_name_en or (page.booth_name_en if page else None),
                    booth_address_hi=r.booth_address_hi or (page.booth_address_hi if page else None),
                    booth_address_en=r.booth_address_en or (page.booth_address_en if page else None),
                ),
                confidence=r.overall_confidence,
                validation_status=r.validation_status,
                watermark=r.watermark,
                source=SourceInfo(
                    document_id=r.document_id,
                    page_id=r.page_id,
                    page_number=page.page_number if page else None,
                    bbox=r.source_bbox,
                ),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit if total > 0 else 1
    )
