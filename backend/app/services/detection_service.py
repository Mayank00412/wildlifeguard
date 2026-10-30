from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
import numpy as np

from app.models.detector import BaseDetector, DetectionResult, get_detector
from app.services.video_processor import VideoProcessor
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FrameDetections:
    frame_idx: int
    timestamp_sec: float
    detections: list[DetectionResult]


class DetectionService:
    """Orchestrates wildlife detection on video frames."""

    def __init__(self, detector: BaseDetector | None = None) -> None:
        self.detector = detector or get_detector()

    def detect_in_frame(self, frame: np.ndarray, frame_idx: int = 0, timestamp_sec: float = 0.0) -> FrameDetections:
        dets = self.detector.detect(frame)
        return FrameDetections(frame_idx=frame_idx, timestamp_sec=timestamp_sec, detections=dets)

    def process_video_stream(
        self,
        video_path: Path,
        target_fps: int | None = None,
        max_frames: int | None = None,
    ) -> list[FrameDetections]:
        processor = VideoProcessor(target_fps=target_fps)
        all_results: list[FrameDetections] = []
        count = 0

        for frame_idx, timestamp, frame in processor.extract_frames(video_path, target_fps=target_fps):
            res = self.detect_in_frame(frame, frame_idx=frame_idx, timestamp_sec=timestamp)
            all_results.append(res)
            count += 1
            if max_frames and count >= max_frames:
                break

        logger.info(
            "Detection completed for %s: %d frames evaluated, %d total animal detections.",
            video_path.name,
            len(all_results),
            sum(len(r.detections) for r in all_results),
        )
        return all_results
