import re
from typing import Optional, Tuple
from app.utils.text_utils import (
    normalize_digits,
    clean_text,
    normalize_gender,
    normalize_relation_type,
    clean_house_number,
    clean_id_number,
)
from app.services.transliteration_service import TransliterationService


class NormalizationService:
    """Service to normalize and transliterate extracted electoral fields."""

    @staticmethod
    def normalize_name(raw_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Clean and transliterate name into (name_hi, name_en)."""
        if not raw_name:
            return None, None
        cleaned = clean_text(raw_name)
        if not cleaned:
            return None, None

        # Check if source is Devanagari or Latin
        has_hindi = any('\u0900' <= ch <= '\u097f' for ch in cleaned)
        if has_hindi:
            # Correct known OCR Devanagari ligature confusion: 'अज्ञान' (ignorance) -> 'अजान' (Azaan)
            # In Indian names 'अजान' is common (e.g. 'अजान प्रसाद', 'अजान मोहम्मद'), whereas 'अज्ञान' is an OCR misread.
            cleaned = re.sub(r'\bअज्ञान\b', 'अजान', cleaned)
            # Clean accidental mixed Latin in Devanagari names
            cleaned = re.sub(r'\bन[iI][kK][hH][iI][lL]\b', 'निखिल', cleaned)
            name_hi = cleaned
            name_en = TransliterationService.hindi_to_english(cleaned)
        else:
            name_en = cleaned
            name_hi = TransliterationService.english_to_hindi(cleaned)

        return name_hi, name_en

    @staticmethod
    def normalize_voter_record(
        serial_number: Optional[int],
        raw_house_number: Optional[str],
        raw_name: Optional[str],
        raw_relation_name: Optional[str],
        raw_relation_label: Optional[str],
        raw_id_number: Optional[str],
        raw_gender: Optional[str],
        raw_age: Optional[int],
        photo_available: bool = False,
        raw_watermark: Optional[str] = None,
    ) -> dict:
        """Normalize all fields of a voter record into the standardized schema."""
        name_hi, name_en = NormalizationService.normalize_name(raw_name)
        rel_hi, rel_en = NormalizationService.normalize_name(raw_relation_name)
        gender_hi, gender_en = normalize_gender(raw_gender)
        rel_type = normalize_relation_type(raw_relation_label)
        house_num = clean_house_number(raw_house_number)
        id_num = clean_id_number(raw_id_number)

        # Sanitize age
        age = None
        if raw_age is not None:
            try:
                age_val = int(normalize_digits(str(raw_age)))
                if 18 <= age_val <= 130:
                    age = age_val
            except (ValueError, TypeError):
                age = None

        # Sanitize watermark/status mark
        watermark = None
        if raw_watermark:
            wm_upper = raw_watermark.strip().upper()
            if any(k in wm_upper for k in ["DELET", "DCUET", "विलोपित"]):
                watermark = "DELETED"
            elif any(k in wm_upper for k in ["MODIF", "संशोधित"]):
                watermark = "MODIFIED"
            elif "DUPLICAT" in wm_upper:
                watermark = "DUPLICATE"
            elif wm_upper:
                watermark = wm_upper

        return {
            "serial_number": serial_number,
            "house_number": house_num,
            "name_hi": name_hi,
            "name_en": name_en,
            "relation_type": rel_type,
            "relation_name_hi": rel_hi,
            "relation_name_en": rel_en,
            "id_number": id_num,
            "gender_hi": gender_hi,
            "gender_en": gender_en,
            "age": age,
            "photo_available": photo_available,
            "watermark": watermark,
        }
