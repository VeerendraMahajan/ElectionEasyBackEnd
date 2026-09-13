from abc import ABC, abstractmethod
from typing import List, Dict, Any
import numpy as np
import pymupdf
from app.schemas.record import VoterExtraction


class BaseExtractor(ABC):
    """Abstract base class for format-specific voter record extractors."""

    @abstractmethod
    def extract_page(
        self,
        page: pymupdf.Page,
        page_image: np.ndarray,
        page_number: int,
        layout_info: Dict[str, Any]
    ) -> List[VoterExtraction]:
        """Extract all voter records from a given page."""
        pass
