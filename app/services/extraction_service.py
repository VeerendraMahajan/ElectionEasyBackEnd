import uuid
from typing import Dict, Any, List, Tuple, Optional
import pymupdf
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.pdf_service import PDFService
from app.services.page_analysis_service import PageAnalysisService
from app.services.duplicate_service import DuplicateService
from app.repositories.page_repository import PageRepository
from app.repositories.record_repository import RecordRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.record import VoterExtraction
from app.core.logging import logger
from app.utils.timing import measure_time


class ExtractionService:
    """Core end-to-end extraction orchestrator for electoral documents."""

    def __init__(self, session: AsyncSession):
        from app.extractors.table_extractor import TableExtractor
        from app.extractors.card_extractor import CardExtractor
        from app.extractors.generic_extractor import GenericExtractor
        from app.extractors.base import BaseExtractor

        self.session = session
        self.page_analysis = PageAnalysisService()
        self.table_extractor = TableExtractor()
        self.card_extractor = CardExtractor()
        self.generic_extractor = GenericExtractor()

        self.doc_repo = DocumentRepository(session)
        self.page_repo = PageRepository(session)
        self.record_repo = RecordRepository(session)

        # Import LLM service for assembly page extraction
        from app.services.llm_service import LLMService
        self.llm_service = LLMService()

    async def process_document_pages(
        self,
        document_id: uuid.UUID,
        pdf_path: str,
        start_page: int = 1,
        end_page: Optional[int] = None,
        progress_callback = None,
        format_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process pages of a document from start_page to end_page (inclusive, 1-indexed).
        Saves page-level hierarchy and voter records in properly normalized tables.
        """
        doc = PDFService.open_pdf(pdf_path)
        total_pages = len(doc)
        end_p = min(end_page or total_pages, total_pages)

        total_extracted_records = 0
        total_failed_records = 0
        pages_processed = 0

        logger.info(f"Starting extraction for document {document_id} ({start_page} to {end_p} of {total_pages} pages)")

        try:
            for p_idx in range(start_page - 1, end_p):
                page_num = p_idx + 1

                with measure_time("page_processing", {"page_number": page_num, "document_id": str(document_id)}):
                    try:
                        # 1. Page Analysis (Rendering + Layout + Header)
                        page, page_img, header_data, layout_info = self.page_analysis.analyze_page(doc, p_idx)
                        layout_type = format_hint or layout_info.get("layout_type")

                        # 2. Persist / Update Page in Database
                        db_page = await self.page_repo.get_by_doc_and_number(document_id, page_num)
                        if not db_page:
                            db_page = await self.page_repo.create(
                                document_id=document_id,
                                page_number=page_num,
                                page_width=page.rect.width,
                                page_height=page.rect.height,
                                extraction_method=str(layout_type),
                                processing_status="PROCESSING"
                            )

                        await self.page_repo.update_header(
                            page_id=db_page.id,
                            header=header_data,
                            raw_header_text=header_data.assembly_name_hi,
                            header_bbox=[0, 0, int(page_img.shape[1]), int(page_img.shape[0] * 0.16)]
                        )

                        # 3. Detect assembly summary page (e.g. demo_1_latest.pdf page 1)
                        if self.page_analysis.is_assembly_summary_page(page, layout_info):
                            logger.info(
                                f"Page {page_num}: Assembly summary/cover page detected — "
                                "extracting metadata via LLM (no voter records on this page)."
                            )
                            # Extract assembly metadata and store it in the page header
                            assembly_data = self.llm_service.extract_assembly_page(
                                page_img, page_num
                            )
                            if assembly_data:
                                # Build a PageHeaderExtraction from the assembly data
                                from app.schemas.page import PageHeaderExtraction
                                enriched_header = PageHeaderExtraction(
                                    assembly_number=assembly_data.get("assembly_number") or header_data.assembly_number,
                                    assembly_name_hi=assembly_data.get("assembly_name_hi") or header_data.assembly_name_hi,
                                    assembly_name_en=None,
                                    section_number=None,
                                    section_name_hi=None,
                                    section_name_en=None,
                                    part_number=assembly_data.get("part_number") or header_data.part_number,
                                    booth_number=assembly_data.get("booth_number"),
                                    booth_name_hi=assembly_data.get("booth_name_hi"),
                                    booth_name_en=None,
                                    booth_address_hi=assembly_data.get("booth_address_hi"),
                                    booth_address_en=None,
                                    page_number=page_num,
                                    confidence=0.97,
                                )
                                await self.page_repo.update_header(
                                    page_id=db_page.id,
                                    header=enriched_header,
                                    raw_header_text=str(assembly_data),
                                    header_bbox=[0, 0, int(page_img.shape[1]), int(page_img.shape[0])]
                                )
                                # Propagate to header_service cache for subsequent voter pages
                                self.page_analysis.header_service.last_valid_header = enriched_header

                            await self.page_repo.update_status(
                                db_page.id, "COMPLETED", method="ASSEMBLY_PAGE"
                            )
                            pages_processed += 1
                            if progress_callback:
                                await progress_callback(pages_delta=1, records_delta=0, failed_delta=0)
                            continue  # No voter records to extract from this page

                        # 4. Route to appropriate voter extractor
                        extractor: BaseExtractor
                        if layout_type == "CARD_FORMAT":
                            extractor = self.card_extractor
                        elif layout_type == "TABLE_FORMAT":
                            extractor = self.table_extractor
                        else:
                            extractor = self.generic_extractor

                        voters: List[VoterExtraction] = extractor.extract_page(page, page_img, page_num, layout_info)

                        # 4. Duplicate Flagging & Validation
                        voters_dicts = [v.model_dump() for v in voters]
                        voters_dicts = DuplicateService.identify_duplicates_in_batch(voters_dicts)
                        final_voters = [VoterExtraction(**vd) for vd in voters_dicts]

                        # 5. Persist Voter Records & Field Results (clean previous records for page first)
                        await self.record_repo.delete_by_page_id(db_page.id)
                        if final_voters:
                            await self.record_repo.create_batch(
                                document_id=document_id,
                                page_id=db_page.id,
                                voters=final_voters
                            )

                        # 6. Update Page Status
                        page_status = "COMPLETED"
                        if any(v.validation_status == "REVIEW_REQUIRED" for v in final_voters):
                            page_status = "REVIEW_REQUIRED"

                        await self.page_repo.update_status(db_page.id, page_status, method=str(layout_type))

                        rec_count = len(final_voters)
                        total_extracted_records += rec_count
                        pages_processed += 1

                        if progress_callback:
                            await progress_callback(
                                pages_delta=1,
                                records_delta=rec_count,
                                failed_delta=0
                            )

                    except Exception as page_err:
                        logger.error(f"Error processing page {page_num} of document {document_id}: {page_err}", exc_info=True)
                        await self.doc_repo.log_error(
                            document_id=document_id,
                            error_type="PAGE_PROCESSING_ERROR",
                            message=f"Page {page_num} failed: {str(page_err)}",
                            stack_trace=str(page_err)
                        )
                        total_failed_records += 1
                        if progress_callback:
                            await progress_callback(pages_delta=1, records_delta=0, failed_delta=1)

            # Update document status
            doc_status = "COMPLETED" if total_failed_records == 0 else "PARTIALLY_COMPLETED"
            await self.doc_repo.update_status(document_id, doc_status, total_pages=total_pages)

            return {
                "document_id": str(document_id),
                "total_pages": total_pages,
                "processed_pages": pages_processed,
                "total_records": total_extracted_records,
                "failed_records": total_failed_records,
                "status": doc_status
            }

        finally:
            doc.close()
