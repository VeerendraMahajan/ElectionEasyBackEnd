from typing import Dict, Any, Tuple
from app.core.config import settings
from app.utils.text_utils import is_text_corrupted


class ValidationService:
    """Deterministic validation service enforcing accuracy and integrity rules."""

    @staticmethod
    def validate_voter_record(record: Dict[str, Any], confidence: float) -> Tuple[str, list[str]]:
        """
        Validate record against electoral consistency rules.
        Returns (validation_status, list_of_warnings_or_errors).
        """
        issues = []

        name = record.get("name_hi") or record.get("name_en")
        age = record.get("age")
        gender = record.get("gender_hi") or record.get("gender_en")
        serial = record.get("serial_number")
        raw_text = record.get("raw_record_text") or ""

        # 1. Critical Failure Check: No name and no serial
        if not name and serial is None:
            return "FAILED", ["Record has neither name nor serial number."]

        # 2. Corrupted Text Check
        if is_text_corrupted(raw_text) and not record.get("name_hi"):
            return "REVIEW_REQUIRED", ["Corrupted Hindi font encoding detected in record."]

        # 3. Age validation
        if age is not None and (age < 18 or age > 130):
            issues.append(f"Invalid age: {age}")

        # 4. Name check
        if not name:
            issues.append("Missing voter name")

        # 5. Low confidence check
        if confidence < settings.REVIEW_REQUIRED_THRESHOLD:
            issues.append(f"Confidence score {confidence:.2f} is below review threshold {settings.REVIEW_REQUIRED_THRESHOLD}")

        # Assign status
        if any("Invalid age" in i or "Missing voter name" in i or "below review threshold" in i for i in issues):
            return "REVIEW_REQUIRED", issues

        if issues or confidence < settings.CONFIDENCE_THRESHOLD:
            return "WARNING", issues

        return "VALID", []
