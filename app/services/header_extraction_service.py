import re
from typing import Optional, Dict, Any, Tuple
import numpy as np
from app.schemas.page import PageHeaderExtraction
from app.utils.font_mapper import decode_legacy_hindi_text
from app.utils.text_utils import normalize_digits, clean_text
from app.services.transliteration_service import TransliterationService
from app.services.llm_service import LLMService
from app.core.logging import logger


class HeaderExtractionService:
    """Service to extract page-level electoral hierarchy from the top header."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()
        self.last_valid_header: Optional[PageHeaderExtraction] = None

    def extract_header_from_text(self, text: str, page_number: int) -> PageHeaderExtraction:
        """
        Deterministic regex-based extraction for Assembly, Section, Part, Booth, and Address.
        Handles both Standard Election Commission formats (PDF 2) and State/Panchayat formats (PDF 1).
        """
        decoded_text = decode_legacy_hindi_text(text)
        norm_text = normalize_digits(decoded_text)
        
        # 1. Assembly Extraction
        # Patterns: विधानसभा निर्वाचन क्षेत्र (संख्या और नाम)? : (\d+)[-\s]+([^\n\r]+)
        assembly_num = None
        assembly_name_hi = None
        assembly_match = re.search(
            r'(?:विधानसभा\s*निर्वाचन\s*क्षेत्र|विधान\s*सभा)[^\d:]*[:\s]*(\d+)[-\s]+([^:\n\r]+?)(?=(?:भाग|अनुभाग|मतदान|$))',
            norm_text, re.IGNORECASE
        )
        if assembly_match:
            assembly_num = assembly_match.group(1).strip()
            assembly_name_hi = clean_text(assembly_match.group(2))
        else:
            # Check for District / Zila format in Panchayat rolls (PDF 1)
            dist_match = re.search(r'(?:जिला|Įÿला)[^\d:]*[:\s]*(\d+)[-\s]+([^\d:]+?)(?=(?:\d+\s*-|विकास|ग्राम|भाग|$))', norm_text)
            if dist_match:
                assembly_num = dist_match.group(1).strip()
                assembly_name_hi = clean_text(dist_match.group(2))

        assembly_name_en = TransliterationService.hindi_to_english(assembly_name_hi) if assembly_name_hi else None

        # 2. Part Number Extraction
        # Pattern: भाग संख्या / सख्या : (\d+)
        part_num = None
        part_match = re.search(r'भाग\s*(?:संख्या|सख्या|नं)?[^\d:]*[:\s]*(\d+)', norm_text)
        if part_match:
            part_num = part_match.group(1).strip()
        else:
            # Check for Vikas Khand / Block number (PDF 1)
            block_match = re.search(r'(?:विकास\s*खंड|Įęकास\s*खंड)[^\d:]*[:\s]*(\d+)', norm_text)
            if block_match:
                part_num = block_match.group(1).strip()

        # 3. Section Extraction
        # Pattern: अनुभाग संख्या और नाम : (\d+)[-\s]+([^\n\r]+)
        section_num = None
        section_name_hi = None
        section_match = re.search(
            r'अनुभाग\s*(?:संख्या|सख्या)\s*(?:और\s*नाम|ओर\s*नाम)?[^\d:]*[:\s]*(\d+)[-\s]+([^:\n\r]+?)(?=(?:मतदान|[A-Z0-9]{3,}|$))',
            norm_text
        )
        if section_match:
            section_num = section_match.group(1).strip()
            section_name_hi = clean_text(section_match.group(2))
        else:
            # Check for Gram Panchayat and Ward Number (PDF 1)
            gp_match = re.search(r'(?:ग्राम\s*पंचायत|Ťाम\s*पंýायत)[^\d:]*[:\s]*(\d+)[-\s]*([^\d:]+?)(?=(?:\d+\s*-|मतदान|सम्बद्ध|$))', norm_text)
            ward_match = re.search(r'(?:वार्ड|ęाडŊ)\s*(?:संख्या|सं)?[^\d:]*[:\s]*(\d+)', norm_text)
            if ward_match:
                section_num = ward_match.group(1).strip()
            elif gp_match:
                section_num = gp_match.group(1).strip()
            if gp_match:
                section_name_hi = clean_text(gp_match.group(2))

        section_name_en = TransliterationService.hindi_to_english(section_name_hi) if section_name_hi else None

        # 4. Booth / Polling Station Extraction
        # Pattern: मतदान (?:केन्द्र|स्थल) (?:संख्या\s*और\s*नाम)?[^\d:]*[:\s]*(\d+)[-\s]+([^\n\r]+)
        booth_num = None
        booth_name_hi = None
        booth_match = re.search(
            r'मतदान\s*(?:केन्द्र|केंद्र)[^\d:]*[:\s]*(\d+)[-\s]*([^\d:]+?)(?=(?:\d+\s*-|सम्बद्ध|मतदान\s*स्थल|$))',
            norm_text
        )
        if not booth_match:
            booth_match = re.search(
                r'मतदान\s*(?:केन्द्र|केंद्र|स्थल|केȾ)[^\d:]*[:\s]*(\d+)[-\s]+([^\n\r]+)',
                norm_text
            )
        if booth_match:
            booth_num = booth_match.group(1).strip()
            booth_name_hi = clean_text(booth_match.group(2))

        booth_name_en = TransliterationService.hindi_to_english(booth_name_hi) if booth_name_hi else None

        # 5. Booth Address Extraction
        booth_addr_hi = booth_name_hi
        booth_addr_en = booth_name_en
        addr_match = re.search(r'मतदान\s*स्थल[^\d:]*[:\s]*([^\n\r]+?)(?=(?:\d+\s*-|वार्ड\s*संख्या|$))', norm_text)
        if not addr_match:
            addr_match = re.search(r'मतदान\s*स्थल\s*का\s*पता[^\n\r:]*[:\s]*([^\n\r]+)', norm_text)
        if addr_match:
            booth_addr_hi = clean_text(addr_match.group(1))
            booth_addr_en = TransliterationService.hindi_to_english(booth_addr_hi)

        # Calculate confidence
        confidence = 0.50
        if assembly_num:
            confidence += 0.20
        if part_num:
            confidence += 0.15
        if section_num:
            confidence += 0.15

        return PageHeaderExtraction(
            assembly_number=assembly_num,
            assembly_name_hi=assembly_name_hi,
            assembly_name_en=assembly_name_en,
            section_number=section_num,
            section_name_hi=section_name_hi,
            section_name_en=section_name_en,
            part_number=part_num,
            booth_number=booth_num,
            booth_name_hi=booth_name_hi,
            booth_name_en=booth_name_en,
            booth_address_hi=booth_addr_hi,
            booth_address_en=booth_addr_en,
            page_number=page_number,
            confidence=min(1.0, round(confidence, 2)),
        )

    def extract_header(
        self,
        header_text: str,
        page_number: int,
        header_crop: Optional[np.ndarray] = None
    ) -> PageHeaderExtraction:
        """Extract header deterministically, inheriting document hierarchy across pages to avoid LLM quota exhaustion."""
        header = self.extract_header_from_text(header_text, page_number)

        # Inherit document hierarchy if already extracted on earlier pages
        if (not header.assembly_number or not header.part_number) and self.last_valid_header:
            logger.info(f"Page {page_number} inheriting header hierarchy from previous page in document")
            header.assembly_number = header.assembly_number or self.last_valid_header.assembly_number
            header.assembly_name_hi = header.assembly_name_hi or self.last_valid_header.assembly_name_hi
            header.assembly_name_en = header.assembly_name_en or self.last_valid_header.assembly_name_en
            header.section_number = header.section_number or self.last_valid_header.section_number
            header.section_name_hi = header.section_name_hi or self.last_valid_header.section_name_hi
            header.section_name_en = header.section_name_en or self.last_valid_header.section_name_en
            header.part_number = header.part_number or self.last_valid_header.part_number
            header.booth_number = header.booth_number or self.last_valid_header.booth_number
            header.booth_name_hi = header.booth_name_hi or self.last_valid_header.booth_name_hi
            header.booth_name_en = header.booth_name_en or self.last_valid_header.booth_name_en
            header.booth_address_hi = header.booth_address_hi or self.last_valid_header.booth_address_hi
            header.booth_address_en = header.booth_address_en or self.last_valid_header.booth_address_en
            header.confidence = max(header.confidence, 0.90)
            return header

        # Only if we have no prior header and LLM is available do we try LLM fallback
        if (not header.assembly_number or not header.part_number) and header_crop is not None and self.llm_service.is_available:
            logger.info(f"Page {page_number} header missing critical fields and no prior header cached, attempting LLM fallback")
            try:
                llm_header = self.llm_service.extract_header(header_crop, header_text, page_number)
                if llm_header and llm_header.assembly_number:
                    self.last_valid_header = llm_header
                    return llm_header
            except Exception as e:
                logger.warning(f"Header LLM fallback error: {e}")

        if header.assembly_number and header.part_number:
            self.last_valid_header = header

        return header
