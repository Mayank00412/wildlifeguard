from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Tuple
import cv2
import numpy as np

from app.core.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VideoStreamMetadata:
    fps: float
    width: int
    height: int
    duration_seconds: float
    total_frames: int
    processing_fps: int


class VideoProcessor:
    """Extracts video stream metadata and yields sampled frames using OpenCV."""

    def __init__(self, target_fps: int | None = None, max_width: int | None = None) -> None:
        settings = get_settings()
        self.target_fps = target_fps or settings.process_fps
        self.max_width = max_width or settings.frame_max_width

    def probe_metadata(self, video_path: Path) -> VideoStreamMetadata:
        """Probe video file using OpenCV and return metadata."""
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"OpenCV could not open video file: {video_path}")

        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

            # Avoid division by zero or invalid fps
            if fps <= 0.0:
                fps = 25.0
            duration = total_frames / fps if total_frames > 0 else 0.0

            return VideoStreamMetadata(
                fps=round(fps, 2),
                width=width,
                height=height,
                duration_seconds=round(duration, 2),
                total_frames=total_frames,
                processing_fps=self.target_fps,
            )
        finally:
            cap.release()

    def extract_frames(
        self,
        video_path: Path,
        target_fps: int | None = None,
        max_width: int | None = None,
    ) -> Generator[Tuple[int, float, np.ndarray], None, None]:
        """
        Yield (frame_index, timestamp_seconds, frame_bgr) at target_fps.
        Samples evenly based on step size between frames.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
        if fps <= 0:
            fps = 25.0

        effective_target_fps = target_fps or self.target_fps
        step = max(1, int(round(fps / effective_target_fps))) if effective_target_fps > 0 else 1
        resize_width = max_width or self.max_width

        frame_idx = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                if frame_idx % step == 0:
                    timestamp = frame_idx / fps
                    # Resize if width exceeds max_width while preserving aspect ratio
                    h, w = frame.shape[:2]
                    if resize_width and w > resize_width:
                        scale = resize_width / float(w)
                        new_h = int(round(h * scale))
                        frame = cv2.resize(frame, (resize_width, new_h), interpolation=cv2.INTER_AREA)

                    yield (frame_idx, round(timestamp, 3), frame)

                frame_idx += 1
        finally:
            cap.release()

    def extract_thumbnail(
        self,
        video_path: Path,
        output_path: Path,
        timestamp_seconds: float = 0.5,
    ) -> bool:
        """Extract a representative frame and save as JPEG thumbnail."""
        if not video_path.exists():
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return False

        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
            target_frame = int(fps * timestamp_seconds)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if total_frames > 0 and target_frame >= total_frames:
                target_frame = 0

            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            if not ret or frame is None:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()

            if ret and frame is not None:
                h, w = frame.shape[:2]
                if w > 640:
                    scale = 640.0 / w
                    frame = cv2.resize(frame, (640, int(round(h * scale))), interpolation=cv2.INTER_AREA)
                cv2.imwrite(str(output_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                return True
            return False
        finally:
            cap.release()

    def extract_and_save_frames(
        self,
        video_path: Path,
        output_dir: Path,
        target_fps: int | None = None,
        max_frames: int = 200,
    ) -> list[Path]:
        """Extract sampled frames and save them to output_dir as JPEGs."""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_paths: list[Path] = []

        count = 0
        for frame_idx, _, frame in self.extract_frames(video_path, target_fps=target_fps):
            frame_path = output_dir / f"frame_{frame_idx:06d}.jpg"
            cv2.imwrite(str(frame_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            saved_paths.append(frame_path)
            count += 1
            if count >= max_frames:
                logger.info("Reached max_frames limit (%d) while extracting frames.", max_frames)
                break

        return saved_paths
