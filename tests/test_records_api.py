import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.person_record import PersonRecord


@pytest.mark.asyncio
async def test_records_search_ascending_order(client: AsyncClient, db_session: AsyncSession):
    """Verify voter records are returned in ascending serial order by default."""
    # Seed document, page, and records
    doc_id = uuid.uuid4()
    page_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        original_filename="sample.pdf",
        file_type="pdf",
        file_size=1024,
        sha256="dummy_hash_" + str(uuid.uuid4())[:8],
        status="COMPLETED",
        total_pages=1,
    )
    db_session.add(doc)

    page = DocumentPage(
        id=page_id,
        document_id=doc_id,
        page_number=1,
        processing_status="COMPLETED",
    )
    db_session.add(page)

    # Insert out-of-order records: 10, 2, 5
    for s_num in [10, 2, 5]:
        r = PersonRecord(
            id=uuid.uuid4(),
            document_id=doc_id,
            page_id=page_id,
            serial_number=s_num,
            name_hi="मतदाता",
            name_en="Voter",
            id_number=f"ID{s_num}",
            age=30,
            overall_confidence=0.95,
            validation_status="VALID",
        )
        db_session.add(r)
    await db_session.commit()

    # Query without sorting params (should default to serial_number asc)
    response = await client.get("/api/v1/records")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    serials = [item["voter"]["serial_number"] for item in data["items"] if item["voter"]["serial_number"] in [2, 5, 10]]
    assert serials == [2, 5, 10]  # Verify strictly ascending sequence


@pytest.mark.asyncio
async def test_review_required_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Verify /records/review-required retrieves records flagged for human review."""
    doc_id = uuid.uuid4()
    page_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        original_filename="review.pdf",
        file_type="pdf",
        file_size=2048,
        sha256="dummy_hash_" + str(uuid.uuid4())[:8],
        status="COMPLETED",
        total_pages=1,
    )
    db_session.add(doc)
    page = DocumentPage(id=page_id, document_id=doc_id, page_number=1, processing_status="COMPLETED")
    db_session.add(page)

    r_review = PersonRecord(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_id=page_id,
        serial_number=99,
        name_hi="संदिग्ध",
        name_en="Ambiguous",
        overall_confidence=0.65,
        validation_status="REVIEW_REQUIRED",
    )
    db_session.add(r_review)
    await db_session.commit()

    response = await client.get("/api/v1/records/review-required")
    assert response.status_code == 200
    data = response.json()
    assert any(item["validation_status"] == "REVIEW_REQUIRED" for item in data["items"])
