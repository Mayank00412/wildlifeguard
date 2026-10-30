from __future__ import annotations

from typing import Sequence
import cv2
import numpy as np

from app.models.classifier import BaseClassifier, ClassificationResult, get_classifier
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ClassificationService:
    """Handles crop extraction, preprocessing, and wildlife species classification."""

    def __init__(self, classifier: BaseClassifier | None = None) -> None:
        self.classifier = classifier or get_classifier()

    def crop_animal(self, frame: np.ndarray, bbox: Sequence[float], pad_ratio: float = 0.05) -> np.ndarray:
        """Safely crop animal bounding box from frame with optional padding."""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in bbox]

        # Add modest padding around bounding box to preserve context
        bw = x2 - x1
        bh = y2 - y1
        pad_x = int(bw * pad_ratio)
        pad_y = int(bh * pad_ratio)

        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)

        if x2 <= x1 or y2 <= y1:
            return np.zeros((10, 10, 3), dtype=np.uint8)

        return frame[y1:y2, x1:x2].copy()

    def classify_detection(self, frame: np.ndarray, bbox: Sequence[float]) -> ClassificationResult:
        crop = self.crop_animal(frame, bbox)
        return self.classifier.classify(crop)
