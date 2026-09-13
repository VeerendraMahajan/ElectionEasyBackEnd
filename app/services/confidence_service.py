from typing import Dict, Any, Optional
from app.utils.text_utils import is_text_corrupted


class ConfidenceService:
    """Computes field-level and overall record confidence using multi-signal scoring."""

    @staticmethod
    def calculate_record_confidence(
        raw_fields: Dict[str, Any],
        ocr_confidence: float = 1.0,
        extraction_method: str = "DETERMINISTIC"
    ) -> float:
        """
        Calculate combined confidence score (0.0 to 1.0) based on:
        - OCR word confidence
        - Field presence (Name, Age, Gender, Serial Number)
        - Text corruption detection
        """
        score = ocr_confidence * 0.40  # 40% base from OCR

        # Field presence checks (40% total)
        has_name = bool(raw_fields.get("name_hi") or raw_fields.get("name_en"))
        has_serial = raw_fields.get("serial_number") is not None
        has_age = raw_fields.get("age") is not None
        has_gender = bool(raw_fields.get("gender_hi") or raw_fields.get("gender_en"))
        has_id = bool(raw_fields.get("id_number"))

        field_points = 0.0
        if has_name:
            field_points += 0.15
        if has_serial:
            field_points += 0.10
        if has_age:
            field_points += 0.05
        if has_gender:
            field_points += 0.05
        if has_id:
            field_points += 0.05

        score += field_points

        # Format & validity check (20%)
        if extraction_method == "DETERMINISTIC":
            score += 0.20
        elif extraction_method == "OCR":
            score += 0.15
        elif extraction_method == "LLM":
            score += 0.10

        # Penalize if text contains corrupted unicode glyphs
        raw_text = raw_fields.get("raw_record_text") or ""
        if is_text_corrupted(raw_text):
            score -= 0.25

        # Bound score between 0.0 and 1.0
        return float(round(max(0.0, min(1.0, score)), 3))
