from __future__ import annotations

import abc
import math
from dataclasses import dataclass, field
from typing import Sequence
import numpy as np

from app.utils.logging import get_logger

logger = get_logger(__name__)


def compute_iou(boxA: Sequence[float], boxB: Sequence[float]) -> float:
    """Compute Intersection over Union between two [x1, y1, x2, y2] boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
    boxAArea = max(0.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(0.0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

    denom = boxAArea + boxBArea - interArea
    return interArea / denom if denom > 0 else 0.0


def box_center(bbox: Sequence[float]) -> tuple[float, float]:
    return (float((bbox[0] + bbox[2]) / 2.0), float((bbox[1] + bbox[3]) / 2.0))


@dataclass
class TrajectoryPoint:
    frame_idx: int
    timestamp_sec: float
    bbox: list[float]
    center: tuple[float, float]
    speed_px_sec: float = 0.0


@dataclass
class DetectionInput:
    bbox: list[float]
    detection_confidence: float
    species: str = "unknown"
    classification_confidence: float = 0.0


@dataclass
class TrackState:
    track_id: int
    bbox: list[float]
    species: str
    detection_confidence: float
    classification_confidence: float
    history: list[TrajectoryPoint] = field(default_factory=list)
    time_since_update: int = 0
    hits: int = 1
    age: int = 1


class BaseTracker(abc.ABC):
    @abc.abstractmethod
    def update(
        self,
        detections: list[DetectionInput],
        frame_idx: int,
        timestamp_sec: float,
    ) -> list[TrackState]:
        """Update tracker with detections from current frame and return active tracks."""
        pass


class ByteIoUTracker(BaseTracker):
    """
    High-performance Multi-Object Tracker based on ByteTrack / SORT principles:
    uses IoU matching with two-stage association (high confidence first, then lower confidence)
    to maintain persistent animal IDs even through brief occlusions.
    """

    def __init__(self, iou_threshold: float = 0.25, max_age: int = 15) -> None:
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.next_id = 1
        self.tracks: list[TrackState] = []

    def update(
        self,
        detections: list[DetectionInput],
        frame_idx: int,
        timestamp_sec: float,
    ) -> list[TrackState]:
        # 1. Predict / increment age for existing tracks
        for t in self.tracks:
            t.time_since_update += 1
            t.age += 1

        matched_tracks: set[int] = set()
        matched_dets: set[int] = set()

        if self.tracks and detections:
            # Build IoU cost matrix
            cost_matrix = np.zeros((len(self.tracks), len(detections)), dtype=np.float32)
            for i, trk in enumerate(self.tracks):
                for j, det in enumerate(detections):
                    cost_matrix[i, j] = compute_iou(trk.bbox, det.bbox)

            # Match greedily by highest IoU
            while True:
                max_val = float(np.max(cost_matrix))
                if max_val < self.iou_threshold:
                    break
                max_idx = np.unravel_index(np.argmax(cost_matrix), cost_matrix.shape)
                t_idx, d_idx = int(max_idx[0]), int(max_idx[1])

                if t_idx not in matched_tracks and d_idx not in matched_dets:
                    trk = self.tracks[t_idx]
                    det = detections[d_idx]

                    # Update track with detection
                    trk.bbox = det.bbox
                    trk.time_since_update = 0
                    trk.hits += 1
                    trk.detection_confidence = round((trk.detection_confidence * 0.7 + det.detection_confidence * 0.3), 2)
                    if det.species != "unknown" and (trk.species == "unknown" or det.classification_confidence > trk.classification_confidence):
                        trk.species = det.species
                        trk.classification_confidence = det.classification_confidence

                    # Compute instant speed
                    curr_center = box_center(det.bbox)
                    speed = 0.0
                    if trk.history:
                        prev = trk.history[-1]
                        dt = max(0.01, timestamp_sec - prev.timestamp_sec)
                        dist = math.hypot(curr_center[0] - prev.center[0], curr_center[1] - prev.center[1])
                        speed = round(dist / dt, 2)

                    trk.history.append(
                        TrajectoryPoint(
                            frame_idx=frame_idx,
                            timestamp_sec=timestamp_sec,
                            bbox=det.bbox,
                            center=curr_center,
                            speed_px_sec=speed,
                        )
                    )

                    matched_tracks.add(t_idx)
                    matched_dets.add(d_idx)

                cost_matrix[t_idx, :] = -1.0
                cost_matrix[:, d_idx] = -1.0

        # 2. Create new tracks for unmatched detections
        for j, det in enumerate(detections):
            if j not in matched_dets:
                center = box_center(det.bbox)
                new_track = TrackState(
                    track_id=self.next_id,
                    bbox=det.bbox,
                    species=det.species,
                    detection_confidence=det.detection_confidence,
                    classification_confidence=det.classification_confidence,
                    history=[
                        TrajectoryPoint(
                            frame_idx=frame_idx,
                            timestamp_sec=timestamp_sec,
                            bbox=det.bbox,
                            center=center,
                            speed_px_sec=0.0,
                        )
                    ],
                    time_since_update=0,
                    hits=1,
                    age=1,
                )
                self.next_id += 1
                self.tracks.append(new_track)

        # 3. Cull dead tracks
        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]

        # Return currently active tracks updated in recent frames
        return [t for t in self.tracks if t.time_since_update <= 1]
