import pymupdf
import numpy as np
from typing import Dict, Any, Tuple
from app.core.config import settings
from app.core.exceptions import PDFProcessingError, FileValidationError
from app.utils.image_utils import render_pdf_page_to_image


class PDFService:
    """Service for opening, inspecting, and rendering PDF documents."""

    @staticmethod
    def open_pdf(pdf_path: str) -> pymupdf.Document:
        try:
            doc = pymupdf.open(pdf_path)
            if doc.is_encrypted or doc.needs_pass:
                doc.close()
                raise FileValidationError("PDF document is password-protected or encrypted. Unprotected files required.")
            return doc
        except FileValidationError:
            raise
        except Exception as e:
            raise PDFProcessingError(f"Failed to open PDF document at {pdf_path}: {str(e)}")

    @staticmethod
    def inspect_pdf(pdf_path: str) -> Dict[str, Any]:
        """Analyze page count, dimensions, text layer presence, and image presence."""
        doc = PDFService.open_pdf(pdf_path)
        try:
            page_count = len(doc)
            if page_count == 0:
                raise FileValidationError("PDF document has 0 pages.")

            if page_count > settings.MAX_PDF_PAGES:
                raise FileValidationError(
                    f"PDF page count ({page_count}) exceeds maximum allowed limit of {settings.MAX_PDF_PAGES} pages."
                )

            # Check sample page
            sample_page = doc[0]
            rect = sample_page.rect
            text = sample_page.get_text().strip()
            images = sample_page.get_images()

            is_scanned = (len(text) < 50 and len(images) > 0)

            return {
                "page_count": page_count,
                "width": rect.width,
                "height": rect.height,
                "has_text": len(text) > 50,
                "is_scanned": is_scanned,
                "total_images_sample": len(images)
            }
        finally:
            doc.close()

    @staticmethod
    def render_page(doc: pymupdf.Document, page_index: int, dpi: int = 150) -> np.ndarray:
        """Render specific page to OpenCV image."""
        try:
            page = doc[page_index]
            return render_pdf_page_to_image(page, dpi=dpi)
        except Exception as e:
            raise PDFProcessingError(f"Failed to render page {page_index + 1}: {str(e)}")
