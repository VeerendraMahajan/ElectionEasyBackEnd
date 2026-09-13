import re
from typing import Optional, Tuple

DEVANAGARI_DIGITS_MAP = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

ARABIC_TO_DEVANAGARI_MAP = {v: k for k, v in DEVANAGARI_DIGITS_MAP.items()}

# Characters indicative of corrupted font glyphs (from KrutiDev/custom mappings into Unicode)
CORRUPTED_HINDI_CHARS = set("æĮęĞũˢƗƕʃčŃýĭĒćđĉĝĳİȶŢ")


def normalize_digits(text: Optional[str]) -> Optional[str]:
    """Convert Devanagari numerals to standard ASCII digits."""
    if not text:
        return text
    res = []
    for ch in text:
        res.append(DEVANAGARI_DIGITS_MAP.get(ch, ch))
    return "".join(res)


def is_text_corrupted(text: Optional[str]) -> bool:
    """Check if text contains corrupted non-standard unicode glyphs."""
    if not text:
        return False
    return any(ch in CORRUPTED_HINDI_CHARS for ch in text)


def clean_text(text: Optional[str]) -> Optional[str]:
    """Clean whitespace, trailing punctuation, and non-printable characters."""
    if not text:
        return None
    cleaned = re.sub(r'[\r\n\t]+', ' ', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = re.sub(r'^[,\-:\s]+|[,\-:\s]+$', '', cleaned)
    return cleaned if cleaned else None


def normalize_gender(raw_gender: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalize gender to (gender_hi, gender_en).
    Examples:
      'पु' / 'पुरुष' / 'Male' / 'M' -> ('पु', 'Male')
      'म' / 'महिला' / 'स्त्री' / 'Female' / 'F' -> ('म', 'Female')
    """
    if not raw_gender:
        return None, None
    g = raw_gender.strip().lower()

    if any(k in g for k in ["महिला", "स्त्री", "female"]) or g == "म" or g == "f":
        return "म", "Female"
    elif any(k in g for k in ["पुरुष", "male"]) or g == "पु" or g == "m":
        return "पु", "Male"
    elif any(k in g for k in ["अन्य", "other", "transgender"]) or g == "t":
        return "अन्य", "Other"

    return None, None


def normalize_relation_type(label: Optional[str]) -> Optional[str]:
    """Identify relation type ('father', 'husband', 'mother', 'other') from raw text/label."""
    if not label:
        return None
    lower = label.lower()
    if any(k in lower for k in ["पिता", "father", "fa"]):
        return "father"
    elif any(k in lower for k in ["पति", "husband", "hu"]):
        return "husband"
    elif any(k in lower for k in ["माता", "mother", "mo"]):
        return "mother"
    elif any(k in lower for k in ["अन्य", "other"]):
        return "other"
    return None


def clean_house_number(raw_house: Optional[str]) -> Optional[str]:
    """
    Ensure house number is cleanly preserved as a string.
    Never converts to integer.
    Supports formats like: '1', '1ब', '15/102', '20ब/3', '34/1'
    """
    if not raw_house:
        return None
    cleaned = clean_text(raw_house)
    if not cleaned:
        return None
    # Remove leading label keywords like 'मकान नं0' or 'House No'
    cleaned = re.sub(r'^(मकान\s*(नं0|संख्या|नं)?[:.\s]*|house\s*(no)?[:.\s]*)', '', cleaned, flags=re.IGNORECASE)
    cleaned = normalize_digits(cleaned)
    cleaned = cleaned.strip()
    return cleaned if cleaned else None


def clean_id_number(raw_id: Optional[str]) -> Optional[str]:
    """
    Clean and validate voter ID / EPIC / SVN numbers.
    Never translates or transliterates IDs.
    Preserves exact alphanumeric structure.
    """
    if not raw_id:
        return None
    cleaned = raw_id.strip().replace(" ", "").upper()
    # Replace common OCR misreads in ID prefixes if obvious (e.g. W"GX -> WGX, !/GX -> WGX)
    cleaned = re.sub(r'^[!|"/]+', '', cleaned)
    cleaned = re.sub(r'["\']', '', cleaned)
    # Check if meets reasonable voter ID pattern
    if len(cleaned) >= 6 and re.search(r'[A-Z0-9]', cleaned):
        return cleaned
    return None
