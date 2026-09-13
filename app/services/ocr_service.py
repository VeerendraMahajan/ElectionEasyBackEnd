import threading
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import easyocr
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import OCRError


class OCRService:
    """
    Singleton OCR Service using EasyOCR for Hindi and English.
    Provides line/word-level bounding boxes and confidence scores.
    """
    _instance: Optional["OCRService"] = None
    _lock = threading.Lock()

    def __init__(self):
        langs = settings.ocr_languages_list
        logger.info(f"Initializing OCR Service with languages: {langs}, GPU={settings.OCR_GPU}")
        try:
            self.reader = easyocr.Reader(langs, gpu=settings.OCR_GPU)
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            raise OCRError(f"Failed to initialize OCR engine: {str(e)}")

    @classmethod
    def get_instance(cls) -> "OCRService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def recognize(
        self,
        image: np.ndarray,
        page_number: int = 1,
        detail: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Run OCR on an OpenCV image (full page or cropped region).
        Returns list of structured records:
        {
            "page_number": page_number,
            "text": "...",
            "bbox": [x1, y1, x2, y2],
            "confidence": 0.95
        }
        """
        try:
            results = self.reader.readtext(image, detail=detail)
            structured_results = []
            for item in results:
                raw_bbox, text, conf = item
                # raw_bbox is 4 corners [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                pts = np.array(raw_bbox, dtype=np.int32)
                x1 = int(np.min(pts[:, 0]))
                y1 = int(np.min(pts[:, 1]))
                x2 = int(np.max(pts[:, 0]))
                y2 = int(np.max(pts[:, 1]))

                structured_results.append({
                    "page_number": page_number,
                    "text": text.strip(),
                    "bbox": [x1, y1, x2, y2],
                    "confidence": float(round(conf, 3)),
                })
            return structured_results
        except Exception as e:
            logger.error(f"OCR recognition error on page {page_number}: {e}")
            raise OCRError(f"OCR execution failed on page {page_number}: {str(e)}")

    @staticmethod
    def preprocess_zone(image: np.ndarray, scale: float = 2.0, binarize: bool = True) -> np.ndarray:
        """Preprocess an image crop to maximize OCR accuracy."""
        if image is None or image.size == 0:
            return image
        import cv2
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        if scale > 1.0:
            gray = cv2.resize(gray, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        if binarize:
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return thresh
        return gray

    def recognize_digits(self, image: np.ndarray) -> Tuple[Optional[int], float]:
        """Extract purely numerical values (such as Serial Number) using digit whitelist."""
        import re
        try:
            prep = self.preprocess_zone(image, scale=2.5, binarize=True)
            results = self.reader.readtext(prep, allowlist="0123456789")
            for _, text, conf in results:
                digits = re.sub(r"[^\d]", "", text)
                if digits and 1 <= len(digits) <= 5:
                    return int(digits), float(conf)

            # Fallback without binarization
            prep_gray = self.preprocess_zone(image, scale=2.0, binarize=False)
            results = self.reader.readtext(prep_gray, allowlist="0123456789")
            for _, text, conf in results:
                digits = re.sub(r"[^\d]", "", text)
                if digits and 1 <= len(digits) <= 5:
                    return int(digits), float(conf)
        except Exception as e:
            logger.debug(f"recognize_digits failed: {e}")
        return None, 0.0

    def recognize_alphanumeric(self, image: np.ndarray) -> Tuple[Optional[str], float]:
        """Extract uppercase alphanumeric strings (such as EPIC / Voter ID) with whitelist."""
        try:
            prep = self.preprocess_zone(image, scale=2.0, binarize=True)
            results = self.reader.readtext(prep, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/-")
            best_text, best_conf = "", 0.0
            for _, text, conf in results:
                clean = text.strip().replace(" ", "").upper()
                if len(clean) > len(best_text):
                    best_text, best_conf = clean, float(conf)
            if best_text:
                return best_text, best_conf

            # Fallback without binarization
            prep_gray = self.preprocess_zone(image, scale=2.0, binarize=False)
            results = self.reader.readtext(prep_gray, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/-")
            for _, text, conf in results:
                clean = text.strip().replace(" ", "").upper()
                if len(clean) > len(best_text):
                    best_text, best_conf = clean, float(conf)
            if best_text:
                return best_text, best_conf
        except Exception as e:
            logger.debug(f"recognize_alphanumeric failed: {e}")
        return None, 0.0

    def recognize_text_only(self, image: np.ndarray) -> str:
        """Helper to quickly OCR a small image crop and return clean combined text."""
        items = self.recognize(image)
        return " ".join(item["text"] for item in items if item["text"])
