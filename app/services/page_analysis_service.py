from typing import Dict, Any, Tuple
import numpy as np
import pymupdf
from app.services.pdf_service import PDFService
from app.services.ocr_service import OCRService
from app.services.header_extraction_service import HeaderExtractionService
from app.services.layout_service import LayoutService, LayoutType
from app.schemas.page import PageHeaderExtraction
from app.utils.image_utils import crop_image_bbox


class PageAnalysisService:
    """Orchestrates page rendering, header extraction, and layout detection."""

    def __init__(
        self,
        ocr_service: OCRService = None,
        header_service: HeaderExtractionService = None
    ):
        self.ocr_service = ocr_service or OCRService.get_instance()
        self.header_service = header_service or HeaderExtractionService()

    def analyze_page(
        self,
        doc: pymupdf.Document,
        page_index: int,
        dpi: int = 150
    ) -> Tuple[pymupdf.Page, np.ndarray, PageHeaderExtraction, Dict[str, Any]]:
        """
        Analyze a single PDF page:
        1. Render page to image
        2. Detect layout (CARD, TABLE, UNKNOWN)
        3. Extract top-left header electoral metadata
        """
        page = doc[page_index]
        page_num = page_index + 1
        page_img = PDFService.render_page(doc, page_index, dpi=dpi)

        # 1. Layout Detection
        layout_info = LayoutService.detect_layout(page, page_img, page_number=page_num)

        # 2. Header Extraction
        # Get header text from text layer or OCR
        h, w = page_img.shape[:2]
        header_crop_box = (0, 0, w, int(h * 0.16))
        header_crop = crop_image_bbox(page_img, header_crop_box)

        text_layer = page.get_text()
        raw_header = ""
        if len(text_layer.strip()) > 50:
            # Use top text blocks for header if genuinely located in the header band (y <= 85)
            header_blocks = [b[4] for b in page.get_text("blocks") if b[3] <= 85]
            raw_header = "\n".join(header_blocks).strip()

        # If digital blocks are missing genuine header text (or lack keywords), OCR the crop
        has_keywords = any(kw in raw_header for kw in ["निर्वाचन", "सभा", "भाग", "जिला", "अनुभाग", "मतदान", "पंचायत", "सूची", "Įÿला", "Ťाम"])
        if not raw_header or not has_keywords:
            raw_header = self.ocr_service.recognize_text_only(header_crop)

        header_data = self.header_service.extract_header(
            header_text=raw_header,
            page_number=page_num,
            header_crop=header_crop
        )

        return page, page_img, header_data, layout_info
