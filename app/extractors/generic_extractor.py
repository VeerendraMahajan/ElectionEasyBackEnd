from typing import List, Dict, Any, Optional
import numpy as np
import pymupdf
from app.extractors.base import BaseExtractor
from app.schemas.record import VoterExtraction
from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.extractors.card_extractor import CardExtractor
from app.extractors.table_extractor import TableExtractor
from app.core.logging import logger


class GenericExtractor(BaseExtractor):
    """
    Adaptive fallback extractor for unknown or irregular layouts.
    Combines full-page OCR analysis and heuristic routing to sub-extractors.
    """

    def __init__(
        self,
        ocr_service: Optional[OCRService] = None,
        llm_service: Optional[LLMService] = None
    ):
        self.ocr_service = ocr_service or OCRService.get_instance()
        self.llm_service = llm_service or LLMService()
        self.card_extractor = CardExtractor(self.ocr_service, self.llm_service)
        self.table_extractor = TableExtractor(self.ocr_service)

    def extract_page(
        self,
        page: pymupdf.Page,
        page_image: np.ndarray,
        page_number: int,
        layout_info: Dict[str, Any]
    ) -> List[VoterExtraction]:
        logger.info(f"Page {page_number}: Using GenericExtractor fallback")

        # Try Card Extractor if any boxes detected
        if layout_info.get("card_boxes"):
            records = self.card_extractor.extract_page(page, page_image, page_number, layout_info)
            if records:
                return records

        # Try Table Extractor
        records = self.table_extractor.extract_page(page, page_image, page_number, layout_info)
        if records:
            return records

        return []
