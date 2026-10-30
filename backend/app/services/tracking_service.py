from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence
import numpy as np

from app.models.tracker import BaseTracker, ByteIoUTracker, DetectionInput, TrackState, TrajectoryPoint
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TrackSummary:
    track_id: int
    species: str
    detection_confidence: float
    classification_confidence: float
    duration_seconds: float
    start_time: float
    end_time: float
    average_speed_px_sec: float
    max_speed_px_sec: float
    total_displacement_px: float
    total_distance_px: float
    direction_vector: tuple[float, float]  # (dx, dy) normalized unit vector
    movement_trend: str
    trajectory: list[dict]


class TrackingService:
    """Manages multi-object tracking and trajectory metrics calculation."""

    def __init__(self, tracker: BaseTracker | None = None) -> None:
        self.tracker = tracker or ByteIoUTracker()
        self.all_completed_tracks: dict[int, TrackState] = {}

    def update(
        self,
        detections: list[DetectionInput],
        frame_idx: int,
        timestamp_sec: float,
    ) -> list[TrackState]:
        active = self.tracker.update(detections, frame_idx, timestamp_sec)
        # Keep references to all tracks for end-of-video analysis
        if isinstance(self.tracker, ByteIoUTracker):
            for t in self.tracker.tracks:
                self.all_completed_tracks[t.track_id] = t
        return active

    def analyze_track(self, track: TrackState) -> TrackSummary:
        pts = track.history
        if not pts:
            return TrackSummary(
                track_id=track.track_id,
                species=track.species,
                detection_confidence=track.detection_confidence,
                classification_confidence=track.classification_confidence,
                duration_seconds=0.0,
                start_time=0.0,
                end_time=0.0,
                average_speed_px_sec=0.0,
                max_speed_px_sec=0.0,
                total_displacement_px=0.0,
                total_distance_px=0.0,
                direction_vector=(0.0, 0.0),
                movement_trend="stationary",
                trajectory=[],
            )

        start_time = pts[0].timestamp_sec
        end_time = pts[-1].timestamp_sec
        duration = max(0.0, end_time - start_time)

        # Distance traveled (cumulative) and speeds
        total_distance = 0.0
        speeds: list[float] = []
        for i in range(1, len(pts)):
            p0 = pts[i - 1].center
            p1 = pts[i].center
            step_dist = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            total_distance += step_dist
            if pts[i].speed_px_sec > 0:
                speeds.append(pts[i].speed_px_sec)

        # Net displacement from start to finish
        dx = pts[-1].center[0] - pts[0].center[0]
        dy = pts[-1].center[1] - pts[0].center[1]
        displacement = math.hypot(dx, dy)

        # Direction unit vector
        norm = displacement if displacement > 0 else 1.0
        dir_vector = (round(dx / norm, 3), round(dy / norm, 3))

        avg_speed = round(float(np.mean(speeds)), 2) if speeds else (round(total_distance / duration, 2) if duration > 0 else 0.0)
        max_speed = round(float(np.max(speeds)), 2) if speeds else avg_speed

        # Movement trend heuristic
        if displacement < 15 and avg_speed < 10:
            trend = "stationary"
        elif total_distance > displacement * 2.5:
            trend = "wandering / meandering"
        else:
            trend = "directional movement"

        traj_serialized = [
            {
                "frame_idx": p.frame_idx,
                "timestamp_sec": p.timestamp_sec,
                "bbox": p.bbox,
                "center": list(p.center),
                "speed_px_sec": p.speed_px_sec,
            }
            for p in pts
        ]

        return TrackSummary(
            track_id=track.track_id,
            species=track.species,
            detection_confidence=track.detection_confidence,
            classification_confidence=track.classification_confidence,
            duration_seconds=round(duration, 2),
            start_time=round(start_time, 2),
            end_time=round(end_time, 2),
            average_speed_px_sec=avg_speed,
            max_speed_px_sec=max_speed,
            total_displacement_px=round(displacement, 2),
            total_distance_px=round(total_distance, 2),
            direction_vector=dir_vector,
            movement_trend=trend,
            trajectory=traj_serialized,
        )

    def get_all_summaries(self) -> list[TrackSummary]:
        return [self.analyze_track(t) for t in self.all_completed_tracks.values()]
