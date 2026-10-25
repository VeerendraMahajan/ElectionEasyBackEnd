import pytest
from app.utils.text_utils import (
    normalize_digits,
    clean_text,
    clean_id_number,
    clean_house_number,
    normalize_gender,
    normalize_relation_type,
)
from app.services.validation_service import ValidationService


def test_normalize_digits_devanagari():
    """Verify Devanagari numerals are converted to standard ASCII digits."""
    assert normalize_digits("१२३४५") == "12345"
    assert normalize_digits("०९८७६") == "09876"
    assert normalize_digits("मकान १२") == "मकान 12"


def test_clean_id_number_epic():
    """Verify EPIC voter ID numbers are cleaned of whitespace and common OCR artifacts."""
    assert clean_id_number(" WGX 1774694 ") == "WGX1774694"
    assert clean_id_number("ztu/1742048") == "ZTU/1742048"


def test_normalize_gender():
    """Verify gender normalization for Hindi and English variations."""
    hi_m, en_m = normalize_gender("पुरुष")
    assert hi_m == "पु"
    assert en_m == "Male"

    hi_f, en_f = normalize_gender("महिला")
    assert hi_f == "म"
    assert en_f == "Female"


def test_normalize_relation_type():
    """Verify relation type normalization."""
    assert normalize_relation_type("पिता का नाम") == "father"
    assert normalize_relation_type("पति का नाम") == "husband"
    assert normalize_relation_type("माता का नाम") == "mother"


def test_clean_house_number():
    """Verify house number extraction supports various Indian electoral patterns."""
    assert clean_house_number("मकान संख्या : 15/102") == "15/102"
    assert clean_house_number("मकान सं.: 1ब") == "1ब"
    assert clean_house_number("House No: 20-A") == "20-A"


def test_validation_service_valid_voter():
    """Verify validation service correctly approves valid voter records."""
    valid_record = {
        "name_hi": "राजेश कुमार",
        "name_en": "Rajesh Kumar",
        "age": 32,
        "gender_hi": "पुरुष",
        "gender_en": "Male",
        "serial_number": 1,
    }
    status, issues = ValidationService.validate_voter_record(valid_record, confidence=0.92)
    assert status == "VALID"
    assert len(issues) == 0


def test_validation_service_underage():
    """Verify underage records (< 18) are flagged for human review."""
    underage_record = {
        "name_hi": "बालक",
        "name_en": "Minor",
        "age": 16,
        "gender_hi": "पुरुष",
        "gender_en": "Male",
        "serial_number": 2,
    }
    status, issues = ValidationService.validate_voter_record(underage_record, confidence=0.90)
    assert status == "REVIEW_REQUIRED"
    assert any("underage" in issue.lower() or "age" in issue.lower() for issue in issues)
