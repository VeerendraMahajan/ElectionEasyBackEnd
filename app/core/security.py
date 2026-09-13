import os
import re
import zipfile
from pathlib import Path
from typing import List, Tuple
from app.core.config import settings
from app.core.exceptions import FileValidationError, UnsupportedFileError

PDF_MAGIC = b"%PDF"
ZIP_MAGIC = b"PK\x03\x04"
ALLOWED_EXTENSIONS = {".pdf", ".zip"}


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and remove illegal characters."""
    # Keep only base name
    clean_name = os.path.basename(filename)
    # Replace dangerous characters with underscores
    clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean_name)
    # Ensure it's not empty
    if not clean_name or clean_name.startswith('.'):
        clean_name = f"document_{clean_name.lstrip('.')}"
    return clean_name


def validate_file_header(file_bytes: bytes) -> str:
    """
    Validate magic bytes / file signature to prevent MIME spoofing.
    Returns detected file type ('pdf' or 'zip').
    """
    if file_bytes.startswith(PDF_MAGIC):
        return "pdf"
    elif file_bytes.startswith(ZIP_MAGIC):
        return "zip"
    else:
        raise FileValidationError("Invalid file signature. Only legitimate PDF and ZIP archives are accepted.")


def validate_file_size(size_bytes: int, is_zip: bool = False) -> None:
    """Validate uploaded file size against configured limits."""
    max_size = settings.MAX_ZIP_SIZE if is_zip else settings.MAX_FILE_SIZE
    if size_bytes > max_size:
        limit_mb = max_size / (1024 * 1024)
        raise FileValidationError(f"File size exceeds maximum allowed limit of {limit_mb:.0f} MB.")


def safe_extract_zip(zip_path: str, extract_to: str) -> List[str]:
    """
    Safely extract ZIP files with defenses against:
    - Path traversal (ZIP slip)
    - ZIP bombs (decompression bombs)
    - Excessive file counts
    
    Returns a list of extracted PDF file paths.
    """
    extract_to_path = Path(extract_to).resolve()
    extract_to_path.mkdir(parents=True, exist_ok=True)
    extracted_pdfs: List[str] = []

    with zipfile.ZipFile(zip_path, 'r') as zf:
        infolist = zf.infolist()

        if len(infolist) > settings.MAX_ZIP_FILES:
            raise FileValidationError(
                f"ZIP contains {len(infolist)} files, exceeding limit of {settings.MAX_ZIP_FILES}."
            )

        total_uncompressed_size = 0

        for member in infolist:
            # Check for decompression bomb
            total_uncompressed_size += member.file_size
            if total_uncompressed_size > settings.MAX_ZIP_EXTRACTED_SIZE:
                limit_mb = settings.MAX_ZIP_EXTRACTED_SIZE / (1024 * 1024)
                raise FileValidationError(
                    f"ZIP uncompressed content exceeds maximum allowed extracted size ({limit_mb:.0f} MB)."
                )

            # Check for path traversal (ZIP slip)
            target_path = (extract_to_path / member.filename).resolve()
            if not str(target_path).startswith(str(extract_to_path)):
                raise FileValidationError(f"Path traversal detected in archive entry: {member.filename}")

            # Ignore directories, skip non-PDFs safely
            if member.is_dir():
                continue

            if member.filename.lower().endswith(".pdf"):
                # Ensure destination parent exists
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source, open(target_path, "wb") as dest:
                    # Stream in 64KB chunks to avoid large memory allocations
                    while chunk := source.read(65536):
                        dest.write(chunk)
                
                # Verify magic bytes of the extracted PDF
                with open(target_path, "rb") as f:
                    header = f.read(4)
                    if header.startswith(PDF_MAGIC):
                        extracted_pdfs.append(str(target_path))

    if not extracted_pdfs:
        raise FileValidationError("No valid PDF documents found inside the ZIP archive.")

    return extracted_pdfs
