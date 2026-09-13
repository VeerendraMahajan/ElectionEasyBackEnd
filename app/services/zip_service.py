import os
from typing import List
from app.core.security import safe_extract_zip
from app.core.logging import logger


class ZipService:
    """Service to safely inspect and extract PDFs from ZIP archives."""

    @staticmethod
    def process_zip(zip_path: str, extract_dir: str) -> List[str]:
        logger.info(f"Extracting ZIP archive: {zip_path} to {extract_dir}")
        pdf_paths = safe_extract_zip(zip_path, extract_dir)
        logger.info(f"Found {len(pdf_paths)} valid PDFs in archive: {zip_path}")
        return pdf_paths
