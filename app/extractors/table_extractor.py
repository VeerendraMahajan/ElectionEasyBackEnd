import re
from typing import List, Dict, Any, Optional
import numpy as np
import pymupdf
from app.extractors.base import BaseExtractor
from app.schemas.record import VoterExtraction
from app.services.normalization_service import NormalizationService
from app.services.confidence_service import ConfidenceService
from app.services.validation_service import ValidationService
from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.utils.font_mapper import decode_legacy_hindi_text
from app.utils.text_utils import normalize_digits, clean_text, clean_id_number, normalize_gender
from app.utils.image_utils import crop_image_bbox
from app.core.config import settings
from app.core.logging import logger


class TableExtractor(BaseExtractor):
    """
    Production-grade extractor for tabular electoral rolls.

    Supports two table formats:
    1. Digital text layer with legacy Indian fonts (KrutiDev / DV-TT)  → deterministic decode.
    2. Scanned tabular image with sparse numeric overlay → Gemini Vision with digital overlay reconciliation.

    Key accuracy improvements:
    - Per-column LLM prompt with exact column-order instructions.
    - Upscaled image crops sent to Gemini for higher text clarity.
    - Row count estimation from the digital overlay to guide LLM completeness.
    - EPIC IDs are taken from the digital overlay (exact string) when available,
      overriding any LLM OCR output for that field.
    """

    def __init__(
        self,
        ocr_service: Optional[OCRService] = None,
        llm_service: Optional[LLMService] = None
    ):
        self.ocr_service = ocr_service or OCRService.get_instance()
        self.llm_service = llm_service or LLMService()

    # ------------------------------------------------------------------
    # Layout heuristic
    # ------------------------------------------------------------------

    def _has_complete_digital_text_layer(self, voter_blocks: List[Any]) -> bool:
        """
        Check if the digital text layer contains genuine elector and relation names
        (such as PAN_076_7_1.pdf with legacy KrutiDev text stream) vs only sparse
        numbers / EPIC overlay (such as sample_data_1.pdf).
        """
        if len(voter_blocks) < 10:
            return False

        sample_blocks = voter_blocks[:min(15, len(voter_blocks))]
        total_lines = 0
        non_ascii_count = 0

        for b in sample_blocks:
            text = b[4]
            lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
            total_lines += len(lines)
            non_ascii_count += len(re.findall(r'[^\x00-\x7F]', text))

        avg_lines = total_lines / len(sample_blocks)
        # Full digital table blocks have ≥5 lines and non-ASCII chars
        return avg_lines >= 5.0 and non_ascii_count >= 5

    def _estimate_rows_from_overlay(self, voter_blocks: List[Any]) -> int:
        """Estimate the number of voter rows per column using the digital overlay serial numbers."""
        serial_nums = []
        for b in voter_blocks:
            text = b[4]
            lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
            if not lines:
                continue
            s = re.sub(r'[^\d]', '', lines[0])
            if s.isdigit() and 1 <= int(s) <= 300:
                serial_nums.append(int(s))

        if not serial_nums:
            return 50  # sensible default

        max_serial = max(serial_nums)
        min_serial = min(serial_nums)

        # Each half-page typically has ~half total rows
        total_rows = max_serial - min_serial + 1
        half_rows = max(25, min(75, (total_rows + 1) // 2))
        return half_rows

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def extract_page(
        self,
        page: pymupdf.Page,
        page_image: np.ndarray,
        page_number: int,
        layout_info: Dict[str, Any]
    ) -> List[VoterExtraction]:
        blocks = page.get_text("blocks")
        voter_blocks = [b for b in blocks if b[1] >= 85 and b[3] <= 838]

        # Case 1: Full digital text with embedded names (e.g. PAN_076_7_1.pdf)
        if self._has_complete_digital_text_layer(voter_blocks):
            logger.info(
                f"Page {page_number}: Using deterministic digital table extraction (legacy font remapping)"
            )
            return self._extract_from_digital_blocks(voter_blocks, page, page_number)

        # Case 2: Scanned tabular image (e.g. sample_data_1.pdf) → Gemini Vision
        if settings.ENABLE_GEMINI_VISION and self.llm_service.is_available:
            logger.info(
                f"Page {page_number}: Using multimodal vision table extraction "
                "with digital overlay cross-validation"
            )
            return self._extract_scanned_table_with_vision(
                page_image, page_number, voter_blocks=voter_blocks
            )

        return []

    # ------------------------------------------------------------------
    # Case 1: Deterministic digital block extraction
    # ------------------------------------------------------------------

    def _extract_from_digital_blocks(
        self,
        voter_blocks: List[Any],
        page: pymupdf.Page,
        page_number: int
    ) -> List[VoterExtraction]:
        """Extract voters deterministically with legacy font remapping in milliseconds."""
        mid_x = page.rect.width * 0.5
        left_blocks = sorted([b for b in voter_blocks if b[0] < mid_x], key=lambda b: b[1])
        right_blocks = sorted([b for b in voter_blocks if b[0] >= mid_x], key=lambda b: b[1])
        ordered_blocks = left_blocks + right_blocks

        extracted: List[VoterExtraction] = []

        for b in ordered_blocks:
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
            if len(lines) < 3:
                continue

            # Line 0: Serial Number
            serial_str = re.sub(r'[^\d]', '', lines[0])
            serial = int(serial_str) if serial_str.isdigit() else None

            # Line 1: House Number
            house_no = decode_legacy_hindi_text(lines[1]) if len(lines) > 1 else None

            # Line 2: Name
            name = decode_legacy_hindi_text(lines[2]) if len(lines) > 2 else None

            # Line 3: Relation Name
            rel_name = decode_legacy_hindi_text(lines[3]) if len(lines) > 3 else None

            # Remaining lines: identify EPIC, Gender, Age regardless of order or missing EPIC
            epic = None
            gender = None
            age = None

            for line in lines[4:]:
                clean_l = clean_text(line)
                if not clean_l:
                    continue

                if not epic and re.match(r'^[A-Z0-9/_-]{6,16}$', clean_l) and not clean_l.isdigit():
                    epic = clean_id_number(clean_l)
                    continue

                if not gender:
                    if clean_l in ["पु", "पुरुष", "Male", "M"]:
                        gender = "पुरुष"
                        continue
                    elif clean_l in ["म", "महिला", "Female", "F"]:
                        gender = "महिला"
                        continue

                if not age:
                    digits = normalize_digits(clean_l)
                    if digits and digits.isdigit() and 18 <= int(digits) <= 130:
                        age = int(digits)
                        continue

            norm_data = NormalizationService.normalize_voter_record(
                serial_number=serial,
                raw_house_number=house_no,
                raw_name=name,
                raw_relation_name=rel_name,
                raw_relation_label="father",
                raw_id_number=epic,
                raw_gender=gender,
                raw_age=age,
                photo_available=False
            )

            voter = VoterExtraction(**norm_data)
            voter.source_bbox = [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]
            voter.raw_record_text = text.strip()

            conf = ConfidenceService.calculate_record_confidence(
                voter.model_dump(),
                ocr_confidence=0.99,
                extraction_method="DETERMINISTIC"
            )
            voter.overall_confidence = conf

            val_status, notes = ValidationService.validate_voter_record(voter.model_dump(), conf)
            voter.validation_status = val_status
            voter.validation_notes = notes

            extracted.append(voter)

        extracted.sort(key=lambda v: (v.serial_number is None, v.serial_number or 0))
        return extracted

    # ------------------------------------------------------------------
    # Case 2: Scanned table — Gemini Vision + overlay reconciliation
    # ------------------------------------------------------------------

    def _extract_scanned_table_with_vision(
        self,
        page_image: np.ndarray,
        page_number: int,
        voter_blocks: Optional[List[Any]] = None
    ) -> List[VoterExtraction]:
        """
        Extract scanned tabular electoral rolls using Gemini Vision with
        digital overlay reconciliation for exact EPIC IDs.
        """
        h, w = page_image.shape[:2]

        # Determine table region — skip header (~10%) and footer (~4%)
        table_top = int(h * 0.10)
        table_bottom = int(h * 0.96)

        # Left and right column crops (50/50 split)
        left_crop = page_image[table_top:table_bottom, 0:int(w * 0.50)]
        right_crop = page_image[table_top:table_bottom, int(w * 0.50):w]

        # Estimate row count per column from digital overlay
        expected_rows = self._estimate_rows_from_overlay(voter_blocks or [])
        logger.info(
            f"Page {page_number}: Estimated {expected_rows} rows per column for LLM extraction."
        )

        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_left = executor.submit(
                self.llm_service.extract_table_slice,
                left_crop, column_side="left", page_number=page_number, expected_rows=expected_rows
            )
            fut_right = executor.submit(
                self.llm_service.extract_table_slice,
                right_crop, column_side="right", page_number=page_number, expected_rows=expected_rows
            )
            left_records = fut_left.result()
            right_records = fut_right.result()

        logger.info(
            f"Page {page_number}: LLM returned {len(left_records)} left + "
            f"{len(right_records)} right rows."
        )

        # Build digital overlay map for exact EPIC IDs and bboxes from text blocks
        overlay_map: Dict[int, Dict[str, Any]] = {}
        if voter_blocks:
            for b in voter_blocks:
                text = b[4]
                lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
                if not lines:
                    continue
                serial_digits = re.sub(r'[^\d]', '', lines[0])
                if not serial_digits.isdigit():
                    continue
                s_num = int(serial_digits)
                epic = None
                age = None
                for line in lines[1:]:
                    cl = clean_text(line)
                    if not cl:
                        continue
                    if not epic and re.match(r'^[A-Z0-9/_-]{6,16}$', cl) and not cl.isdigit():
                        epic = clean_id_number(cl)
                    elif not age:
                        d = normalize_digits(cl)
                        if d and d.isdigit() and 18 <= int(d) <= 130:
                            age = int(d)
                overlay_map[s_num] = {
                    "epic": epic,
                    "age": age,
                    "bbox": [round(b[0], 1), round(b[1], 1), round(b[2], 1), round(b[3], 1)],
                    "raw_text": text.strip()
                }

        all_records = left_records + right_records
        results: List[VoterExtraction] = []

        for item in all_records:
            s_num = item.get("serial_number")
            overlay = overlay_map.get(s_num) if s_num else None

            # Prefer exact digital EPIC over LLM OCR (digital text is always more accurate)
            epic = overlay.get("epic") if (overlay and overlay.get("epic")) else item.get("id_number")
            bbox = overlay.get("bbox") if (overlay and overlay.get("bbox")) else [0, 0, 0, 0]
            raw_txt = f"{item.get('name_hi', '')} | {epic or ''}"

            norm_data = NormalizationService.normalize_voter_record(
                serial_number=s_num,
                raw_house_number=item.get("house_number"),
                raw_name=item.get("name_hi"),
                raw_relation_name=item.get("relation_name_hi"),
                raw_relation_label=item.get("relation_type", "father"),
                raw_id_number=epic,
                raw_gender=item.get("gender"),
                raw_age=item.get("age") or (overlay.get("age") if overlay else None),
                photo_available=False
            )
            voter = VoterExtraction(**norm_data)
            voter.source_bbox = bbox
            voter.raw_record_text = raw_txt
            voter.watermark = item.get("watermark")

            conf = ConfidenceService.calculate_record_confidence(
                voter.model_dump(),
                ocr_confidence=0.99 if overlay else 0.97,
                extraction_method="HYBRID" if overlay else "LLM_VISION"
            )
            voter.overall_confidence = conf

            val_status, notes = ValidationService.validate_voter_record(voter.model_dump(), conf)
            voter.validation_status = val_status
            voter.validation_notes = notes

            results.append(voter)

        results.sort(key=lambda v: (v.serial_number is None, v.serial_number or 0))
        return results
