import cv2
import numpy as np
import pymupdf
from typing import List, Tuple, Optional


def render_pdf_page_to_image(page: pymupdf.Page, dpi: int = 150) -> np.ndarray:
    """Render a PyMuPDF page to an OpenCV BGR numpy image at specified DPI."""
    pix = page.get_pixmap(dpi=dpi)
    img_bytes = pix.tobytes("png")
    nparr = np.frombuffer(img_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img_bgr


def crop_image_bbox(img: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
    """Crop image with [x1, y1, x2, y2] coordinates with bounds safety."""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in bbox]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return np.zeros((10, 10, 3), dtype=np.uint8)
    return img[y1:y2, x1:x2]


def detect_card_grid_boxes(img: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Dynamically detect rectangular voter card bounding boxes using OpenCV morphology.
    Returns sorted list of [x1, y1, x2, y2] bounding boxes in reading order (top-to-bottom, left-to-right).
    Does NOT hardcode 30 cards or fixed coordinates.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)

    h, w = img.shape[:2]
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(w / 30), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(h / 30)))

    h_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, v_kernel)
    table_grid = cv2.add(h_lines, v_lines)

    contours, _ = cv2.findContours(table_grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    raw_boxes = []

    for c in contours:
        x, y, bw_c, bh_c = cv2.boundingRect(c)
        # Card aspect filter: typical card is ~20% to 40% page width and 6% to 15% page height
        if 0.20 * w < bw_c < 0.40 * w and 0.05 * h < bh_c < 0.15 * h:
            raw_boxes.append([x, y, x + bw_c, y + bh_c])

    if not raw_boxes:
        return []

    # Deduplicate concentric/nested border boxes via Non-Maximum Suppression (IoU)
    unique_boxes: List[List[int]] = []
    for b in sorted(raw_boxes, key=lambda box: (box[2] - box[0]) * (box[3] - box[1]), reverse=True):
        overlap = False
        for u in unique_boxes:
            ix1 = max(b[0], u[0])
            iy1 = max(b[1], u[1])
            ix2 = min(b[2], u[2])
            iy2 = min(b[3], u[3])
            if ix2 > ix1 and iy2 > iy1:
                inter = (ix2 - ix1) * (iy2 - iy1)
                b_area = (b[2] - b[0]) * (b[3] - b[1])
                if inter / b_area > 0.6:
                    overlap = True
                    break
        if not overlap:
            unique_boxes.append(b)

    # Sort row-major: cluster by row (grouping by height tolerance), then by x
    row_height_tol = int(h * 0.04)
    sorted_boxes = sorted(unique_boxes, key=lambda b: (round(b[1] / row_height_tol) * row_height_tol, b[0]))
    return [tuple(b) for b in sorted_boxes]
