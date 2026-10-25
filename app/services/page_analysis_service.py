from typing import Dict, Any, Tuple, Optional
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
        dpi: int = 200
    ) -> Tuple[pymupdf.Page, np.ndarray, PageHeaderExtraction, Dict[str, Any]]:
        """
        Analyze a single PDF page:
        1. Render page to image at higher DPI (200) for better OCR/LLM quality.
        2. Detect layout (CARD, TABLE, UNKNOWN).
        3. Extract top-left header electoral metadata.
        """
        page = doc[page_index]
        page_num = page_index + 1
        page_img = PDFService.render_page(doc, page_index, dpi=dpi)

        # 1. Layout Detection
        layout_info = LayoutService.detect_layout(page, page_img, page_number=page_num)

        # 2. Header Extraction
        h, w = page_img.shape[:2]
        header_crop_box = (0, 0, w, int(h * 0.16))
        header_crop = crop_image_bbox(page_img, header_crop_box)

        text_layer = page.get_text()
        raw_header = ""
        if len(text_layer.strip()) > 50:
            # Use top text blocks for header if they are in the header band (y <= 85)
            header_blocks = [b[4] for b in page.get_text("blocks") if b[3] <= 85]
            raw_header = "\n".join(header_blocks).strip()

        # If digital blocks are missing genuine header text (or lack keywords), OCR the crop
        has_keywords = any(
            kw in raw_header
            for kw in [
                "निर्वाचन", "सभा", "भाग", "जिला", "अनुभाग", "मतदान",
                "पंचायत", "सूची", "Įÿला", "Ťाम",
            ]
        )
        if not raw_header or not has_keywords:
            raw_header = self.ocr_service.recognize_text_only(header_crop)

        header_data = self.header_service.extract_header(
            header_text=raw_header,
            page_number=page_num,
            header_crop=header_crop
        )

        return page, page_img, header_data, layout_info

    def is_assembly_summary_page(self, page: pymupdf.Page, layout_info: Dict[str, Any]) -> bool:
        """
        Detect whether this page is the Assembly Details summary form (Page 1 of demo_1_latest.pdf).
        Heuristics:
        - Layout is UNKNOWN (no card grid, no table text blocks).
        - Page has no voter blocks at all but has a large scanned image.
        """
        is_unknown = layout_info.get("layout_type") in [LayoutType.UNKNOWN_FORMAT, "UNKNOWN_FORMAT"]
        page_text = page.get_text().strip()
        images = page.get_images()
        # Assembly page: scanned image, no extractable text, not card or table layout
        return is_unknown and len(page_text) < 50 and len(images) > 0

    def extract_cover_page_deterministic(self, page_img: np.ndarray, page_num: int = 1) -> Dict[str, Any]:
        """
        Deterministic OCR-based extraction of cover / assembly details page (Page 1).
        Extracts assembly, part, booth number, booth name, and booth address directly from OCR.
        """
        import re
        from app.utils.text_utils import normalize_digits, clean_text
        from app.services.transliteration_service import TransliterationService

        ocr_results = self.ocr_service.recognize(page_img, page_number=page_num)
        lines = [r["text"].strip() for r in ocr_results if r.get("text")]
        raw_text = "\n".join(lines)
        norm_text = normalize_digits(raw_text)

        data = {"page_number": page_num}

        # 1. Assembly number & name
        asm_match = re.search(r'(?:विधानसभा.*?|विधान\s*सभा)[^\d:\n]*[:\s]*(\d+)\s*[-:]\s*([^\(\n\r]+)', norm_text)
        if asm_match:
            data["assembly_number"] = asm_match.group(1).strip()
            data["assembly_name_hi"] = clean_text(asm_match.group(2))
            data["assembly_name_en"] = TransliterationService.hindi_to_english(data["assembly_name_hi"])

        # 2. Part number
        part_match = re.search(r'भाग\s*(?:संख्या|सख्या|नं)?[^\d:\n]*[:\s]*(\d+)', norm_text)
        if part_match:
            data["part_number"] = part_match.group(1).strip()

        # 3. Booth number and name
        booth_match = re.search(
            r'मतदान\s*स्थल\s*की\s*संख्या\s*और\s*नाम[\s\S]*?(?:^|\n)\s*(\d+)\s*(?:-\s*)?([^\n\r]+)',
            norm_text
        )
        if not booth_match:
            booth_match = re.search(r'मतदान\s*(?:स्थल|केन्द्र|केंद्र)[^\d:\n]*[:\s]*(\d+)\s*[-:]?\s*([^\n\r]+)', norm_text)
        if booth_match:
            data["booth_number"] = booth_match.group(1).strip()
            data["booth_name_hi"] = clean_text(booth_match.group(2))
            data["booth_name_en"] = TransliterationService.hindi_to_english(data["booth_name_hi"])

        # 4. Booth address
        addr_match = re.search(
            r'मतदान\s*स्थल\s*का\s*पता[\s\S]*?(?:^|\n)\s*([^\n\r]+)',
            norm_text
        )
        if addr_match:
            b_addr = clean_text(addr_match.group(1))
            if b_addr and "निर्वाचक" not in b_addr and "विवरण" not in b_addr:
                data["booth_address_hi"] = b_addr
                data["booth_address_en"] = TransliterationService.hindi_to_english(b_addr)
        if not data.get("booth_address_hi") and data.get("booth_name_hi"):
            data["booth_address_hi"] = data["booth_name_hi"]
            data["booth_address_en"] = data.get("booth_name_en")

        return data
