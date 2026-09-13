from typing import List, Dict, Any, Tuple
import numpy as np
import pymupdf
from app.utils.image_utils import crop_image_bbox
from app.services.ocr_service import OCRService


class RecordSegmentationService:
    """Service to segment individual voter record regions from pages."""

    def __init__(self, ocr_service: OCRService = None):
        self.ocr_service = ocr_service or OCRService.get_instance()

    def segment_records(
        self,
        page: pymupdf.Page,
        page_image: np.ndarray,
        page_number: int,
        layout_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Segment records into localized crops with bounding boxes and OCR evidence.
        """
        segments: List[Dict[str, Any]] = []

        if layout_info.get("layout_type") == "CARD_FORMAT":
            card_boxes = layout_info.get("card_boxes", [])
            for idx, box in enumerate(card_boxes):
                crop = crop_image_bbox(page_image, box)
                ocr_results = self.ocr_service.recognize(crop, page_number=page_number)
                text = "\n".join(r["text"] for r in ocr_results if r["text"])
                conf = (
                    sum(r["confidence"] for r in ocr_results) / len(ocr_results)
                    if ocr_results else 0.5
                )

                segments.append({
                    "page_number": page_number,
                    "record_index": idx + 1,
                    "bbox": list(box),
                    "crop_image": crop,
                    "ocr_text": text,
                    "ocr_confidence": round(conf, 3),
                    "extraction_method": "CARD_OCR"
                })

        elif layout_info.get("layout_type") == "TABLE_FORMAT":
            blocks = page.get_text("blocks")
            voter_blocks = [b for b in blocks if b[1] >= 90 and b[3] <= 835]
            img_h, img_w = page_image.shape[:2]
            scale_x = img_w / page.rect.width
            scale_y = img_h / page.rect.height

            for idx, b in enumerate(voter_blocks):
                x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
                pixel_bbox = (
                    int(x0 * scale_x),
                    int(y0 * scale_y),
                    int(x1 * scale_x),
                    int(y1 * scale_y)
                )
                crop = crop_image_bbox(page_image, pixel_bbox)

                segments.append({
                    "page_number": page_number,
                    "record_index": idx + 1,
                    "bbox": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                    "crop_image": crop,
                    "ocr_text": text.strip(),
                    "ocr_confidence": 0.95,
                    "extraction_method": "TABLE_TEXT"
                })

        return segments
