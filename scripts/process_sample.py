import asyncio
import os
import sys
import json
import time
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from app.core.database import Base
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.person_record import PersonRecord
from app.services.extraction_service import ExtractionService
from app.repositories.document_repository import DocumentRepository
from app.utils.hashing import calculate_sha256
from app.services.pdf_service import PDFService


async def process_pdf(pdf_path: str, session: AsyncSession, max_pages: int = 5) -> dict:
    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"Sample PDF not found at {pdf_path}")

    filename = pdf_path_obj.name
    sha256_hash = calculate_sha256(str(pdf_path_obj))
    file_size = os.path.getsize(str(pdf_path_obj))
    meta = PDFService.inspect_pdf(str(pdf_path_obj))
    total_pages = meta["page_count"]

    doc_repo = DocumentRepository(session)
    existing = await doc_repo.get_by_sha256(sha256_hash)
    if existing:
        doc = existing
    else:
        doc = await doc_repo.create(
            original_filename=filename,
            file_type="pdf",
            file_size=file_size,
            sha256_hash=sha256_hash,
            total_pages=total_pages,
            status="PROCESSING"
        )
        await session.commit()

    print(f"\n============================================================")
    print(f"PROCESSING: {filename} ({total_pages} pages)")
    print(f"============================================================")

    ext_service = ExtractionService(session)
    start_time = time.perf_counter()

    # Process first max_pages for speed & sample validation (e.g. 5 pages per sample PDF)
    pages_to_run = min(total_pages, max_pages)
    res = await ext_service.process_document_pages(
        document_id=doc.id,
        pdf_path=str(pdf_path_obj),
        start_page=1,
        end_page=pages_to_run
    )
    await session.commit()
    elapsed_sec = time.perf_counter() - start_time

    # Collect statistics from database
    pages_stmt = select(DocumentPage).where(DocumentPage.document_id == doc.id).order_by(DocumentPage.page_number)
    pages = (await session.execute(pages_stmt)).scalars().all()

    records_stmt = select(PersonRecord).where(PersonRecord.document_id == doc.id)
    records = (await session.execute(records_stmt)).scalars().all()

    valid_count = sum(1 for r in records if r.validation_status == "VALID")
    warning_count = sum(1 for r in records if r.validation_status == "WARNING")
    review_count = sum(1 for r in records if r.validation_status == "REVIEW_REQUIRED")
    failed_count = sum(1 for r in records if r.validation_status == "FAILED")
    avg_conf = sum(r.overall_confidence for r in records) / len(records) if records else 0.0

    # Print sample extracted header & voter records
    print(f"\n[PAGE 1 HEADER EXTRACTION]")
    if pages:
        p1 = pages[0]
        print(f"  Assembly : {p1.assembly_number} - {p1.assembly_name_hi} ({p1.assembly_name_en})")
        print(f"  Section  : {p1.section_number} - {p1.section_name_hi} ({p1.section_name_en})")
        print(f"  Part     : {p1.part_number}")
        print(f"  Booth    : {p1.booth_number} - {p1.booth_name_hi} ({p1.booth_name_en})")
        print(f"  Address  : {p1.booth_address_hi} ({p1.booth_address_en})")

    print(f"\n[SAMPLE EXTRACTED VOTER RECORDS (Showing first 3)]")
    for idx, r in enumerate(records[:3]):
        print(f"  Voter {idx+1}:")
        print(f"    Serial  : {r.serial_number}")
        print(f"    House   : {r.house_number}")
        print(f"    Name    : {r.name_hi} ({r.name_en})")
        print(f"    Relation: {r.relation_type}: {r.relation_name_hi} ({r.relation_name_en})")
        print(f"    ID      : {r.id_number}")
        print(f"    Gender  : {r.gender_hi} ({r.gender_en})")
        print(f"    Age     : {r.age}")
        print(f"    Booth   : {r.booth_number} - {r.booth_name_hi} ({r.booth_name_en})")
        print(f"    Address : {r.booth_address_hi} ({r.booth_address_en})")
        print(f"    Status  : {r.validation_status} (Confidence: {r.overall_confidence:.2f})")

    report = {
        "document": filename,
        "total_pdf_pages": total_pages,
        "pages_processed": pages_to_run,
        "records_detected": len(records),
        "records_valid": valid_count,
        "records_warning": warning_count,
        "records_review_required": review_count,
        "records_failed": failed_count,
        "average_confidence": round(avg_conf, 3),
        "records_per_page": round(len(records) / pages_to_run, 1) if pages_to_run else 0,
        "processing_time_seconds": round(elapsed_sec, 2),
        "avg_time_per_page_seconds": round(elapsed_sec / pages_to_run, 2) if pages_to_run else 0,
        "header_extraction_status": "SUCCESS" if (pages and pages[0].assembly_number) else "PARTIAL"
    }

    print(f"\n[EXTRACTION QUALITY REPORT FOR {filename}]")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    return report


async def main():
    db_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./electoral_test.db")
    try:
        engine = create_async_engine(db_url, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"Warning: Primary database ({db_url}) failed: {e}. Falling back to SQLite local database.")
        db_url = "sqlite+aiosqlite:///./electoral_test.db"
        engine = create_async_engine(db_url, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    reports = []
    async with session_factory() as session:
        # Sample 1: PAN_076_7_1.pdf (Table layout)
        pdf1 = "sample_data/PAN_076_7_1.pdf"
        r1 = await process_pdf(pdf1, session, max_pages=2)
        reports.append(r1)

        # Sample 2: PDF Format New-3-38.pdf (Card grid layout)
        pdf2 = "sample_data/PDF Format New-3-38.pdf"
        r2 = await process_pdf(pdf2, session, max_pages=2)
        reports.append(r2)

    # Save extraction quality report artifact
    report_path = "reports/sample_extraction_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)

    print("\n" + "="*60)
    print(f"All sample processing completed successfully. Report saved to {report_path}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
