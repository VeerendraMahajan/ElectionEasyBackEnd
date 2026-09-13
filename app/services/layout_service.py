from enum import Enum
from typing import Dict, Any, List, Tuple
import numpy as np
import pymupdf
from app.utils.image_utils import detect_card_grid_boxes


class LayoutType(str, Enum):
    TABLE_FORMAT = "TABLE_FORMAT"
    CARD_FORMAT = "CARD_FORMAT"
    UNKNOWN_FORMAT = "UNKNOWN_FORMAT"


class LayoutService:
    """Service to detect document and page layout format and structure."""

    @staticmethod
    def detect_layout(
        page: pymupdf.Page,
        page_image: np.ndarray,
        page_number: int = 1
    ) -> Dict[str, Any]:
        """
        Analyze page visual structure and text layer to determine layout format:
        - CARD_FORMAT: Grid of rectangular voter cards
        - TABLE_FORMAT: Tabular list with columns and rows
        - UNKNOWN_FORMAT: Fallback
        """
        # Step 1: Detect grid cards via OpenCV
        card_boxes = detect_card_grid_boxes(page_image)
        if len(card_boxes) >= 6:
            return {
                "layout_type": LayoutType.CARD_FORMAT,
                "card_count": len(card_boxes),
                "card_boxes": card_boxes,
                "is_table": False
            }

        # Step 2: Check PDF text layer for table structure
        blocks = page.get_text("blocks")
        voter_blocks = [b for b in blocks if b[1] >= 80 and b[3] <= 830]

        # Check if side-by-side columns exist (e.g. PDF 1 format)
        left_blocks = [b for b in voter_blocks if b[0] < page.rect.width * 0.5]
        right_blocks = [b for b in voter_blocks if b[0] >= page.rect.width * 0.5]

        if len(voter_blocks) >= 20 or (len(left_blocks) >= 10 and len(right_blocks) >= 10):
            return {
                "layout_type": LayoutType.TABLE_FORMAT,
                "card_count": 0,
                "card_boxes": [],
                "is_table": True,
                "has_side_by_side": len(right_blocks) >= 10
            }

        return {
            "layout_type": LayoutType.UNKNOWN_FORMAT,
            "card_count": len(card_boxes),
            "card_boxes": card_boxes,
            "is_table": False
        }
