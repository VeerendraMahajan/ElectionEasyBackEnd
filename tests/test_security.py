import io
import zipfile
import pytest
from app.core.security import (
    sanitize_filename,
    validate_file_header,
    validate_file_size,
    safe_extract_zip,
    PDF_MAGIC,
    ZIP_MAGIC,
)
from app.core.exceptions import FileValidationError


def test_sanitize_filename_traversal():
    """Verify directory traversal is stripped from filenames."""
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\boot.ini") == "boot.ini"
    assert sanitize_filename("test/nested/file.pdf") == "file.pdf"


def test_sanitize_filename_null_bytes_and_illegal_chars():
    """Verify null bytes and dangerous shell characters are neutralized."""
    sanitized = sanitize_filename("sample\x00_file;rm -rf.pdf")
    assert "\x00" not in sanitized
    assert ";" not in sanitized
    assert " " not in sanitized


def test_validate_file_header_valid():
    """Verify legitimate PDF and ZIP magic bytes are accepted."""
    assert validate_file_header(b"%PDF-1.4 sample content") == "pdf"
    assert validate_file_header(b"PK\x03\x04\x14\x00") == "zip"


def test_validate_file_header_spoofed_extension():
    """Verify text or executable files spoofed as PDF/ZIP are rejected."""
    with pytest.raises(FileValidationError, match="Invalid file signature"):
        validate_file_header(b"<html><script>alert(1)</script></html>")

    with pytest.raises(FileValidationError, match="Invalid file signature"):
        validate_file_header(b"MZ\x90\x00\x03\x00\x00\x00")  # Windows PE binary


def test_validate_file_size_empty_file():
    """Verify 0-byte empty files are rejected."""
    with pytest.raises(FileValidationError, match="empty"):
        validate_file_size(0)


def test_validate_file_size_oversized():
    """Verify files exceeding size limits are rejected."""
    with pytest.raises(FileValidationError, match="exceeds maximum"):
        validate_file_size(60 * 1024 * 1024, is_zip=False)  # 60MB > 50MB limit


def test_safe_extract_zip_path_traversal(tmp_path):
    """Verify ZIP slip path traversal entries are rejected."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        # Malicious entry attempting to escape extraction directory
        zf.writestr("../../evil.pdf", b"%PDF-1.5 fake content")

    zip_file = tmp_path / "malicious.zip"
    zip_file.write_bytes(zip_buffer.getvalue())

    dest_dir = tmp_path / "extracted"
    with pytest.raises(FileValidationError, match="Path traversal detected"):
        safe_extract_zip(str(zip_file), str(dest_dir))


def test_safe_extract_zip_valid(tmp_path):
    """Verify safe extraction of legitimate PDF inside ZIP."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("subfolder/legitimate.pdf", b"%PDF-1.4 clean pdf content")

    zip_file = tmp_path / "valid.zip"
    zip_file.write_bytes(zip_buffer.getvalue())

    dest_dir = tmp_path / "extracted"
    extracted = safe_extract_zip(str(zip_file), str(dest_dir))
    assert len(extracted) == 1
    assert "legitimate.pdf" in extracted[0]
