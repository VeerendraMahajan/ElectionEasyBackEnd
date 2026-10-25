import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from app.api.dependencies import get_record_repository
from app.repositories.record_repository import RecordRepository
from app.schemas.record import (
    PersonRecordResponse,
    PersonRecordUpdate,
    LocationInfo,
    VoterInfo,
    SourceInfo,
    FieldResultResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.validation_service import ValidationService

router = APIRouter(prefix="/records", tags=["records"])


def _to_response(r) -> PersonRecordResponse:
    page = r.page
    return PersonRecordResponse(
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


@router.get("", response_model=PaginatedResponse[PersonRecordResponse])
async def search_records(
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
    sort_by: str = Query("serial_number", description="Field to sort by (serial_number, age, name)"),
    sort_order: str = Query("asc", description="Sort order ('asc' for 1,2,3... or 'desc')"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    repo: RecordRepository = Depends(get_record_repository),
):
    """Search and filter extracted voter records in ascending order by serial number by default."""
    records, total = await repo.search(
        document_id=document_id,
        page_id=page_id,
        page_number=page_number,
        assembly_number=assembly_number,
        section_number=section_number,
        part_number=part_number,
        booth_number=booth_number,
        gender=gender,
        id_number=id_number,
        house_number=house_number,
        min_age=min_age,
        max_age=max_age,
        validation_status=validation_status,
        min_confidence=min_confidence,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )

    items = [_to_response(r) for r in records]
    return PaginatedResponse(
        items=items,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit if total > 0 else 1
    )


@router.get("/review-required", response_model=PaginatedResponse[PersonRecordResponse])
async def get_records_for_review(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    repo: RecordRepository = Depends(get_record_repository),
):
    """Get low-confidence or ambiguous voter records requiring human review."""
    records, total = await repo.get_review_required(skip=skip, limit=limit)
    items = [_to_response(r) for r in records]
    return PaginatedResponse(
        items=items,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit if total > 0 else 1
    )


@router.get("/{record_id}", response_model=PersonRecordResponse)
async def get_record_by_id(
    record_id: uuid.UUID,
    repo: RecordRepository = Depends(get_record_repository),
):
    """Get single voter record by UUID with associated electoral location details."""
    record = await repo.get_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Person record not found.")
    return _to_response(record)


@router.patch("/{record_id}", response_model=PersonRecordResponse)
async def update_record(
    record_id: uuid.UUID,
    update_data: PersonRecordUpdate,
    repo: RecordRepository = Depends(get_record_repository),
):
    """Apply human review corrections to a voter record while preserving audit history."""
    updated = await repo.update_record(record_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Person record not found.")
    return _to_response(updated)


@router.post("/{record_id}/validate")
async def validate_single_record(
    record_id: uuid.UUID,
    repo: RecordRepository = Depends(get_record_repository),
):
    """Re-run deterministic validation checks on an existing voter record."""
    record = await repo.get_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Person record not found.")

    status, issues = ValidationService.validate_voter_record(
        {
            "name_hi": record.name_hi,
            "name_en": record.name_en,
            "age": record.age,
            "gender_hi": record.gender_hi,
            "gender_en": record.gender_en,
            "serial_number": record.serial_number,
            "raw_record_text": record.raw_record_text,
        },
        confidence=record.overall_confidence
    )

    return {
        "record_id": record.id,
        "validation_status": status,
        "issues": issues,
        "is_valid": status == "VALID"
    }
