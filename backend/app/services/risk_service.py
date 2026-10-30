from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.models.risk_model import BaseRiskEngine, RiskAssessment, get_risk_engine
from app.models.tracker import TrackState
from app.services.tracking_service import TrackSummary
from app.utils.geometry import calculate_movement_direction, is_point_in_polygon, point_to_polygon_distance
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RiskEvent:
    event_id: str
    track_id: int
    species: str
    timestamp_sec: float
    frame_idx: int
    risk_score: int
    risk_level: str
    factors: list[str]
    confidence: float
    distance_image_space: float
    direction: str
    behavior: str


class RiskService:
    """Manages encounter-risk evaluation and detects notable risk events."""

    def __init__(self, engine: BaseRiskEngine | None = None) -> None:
        self.engine = engine or get_risk_engine()

    def evaluate_track_risk(
        self,
        track_summary: TrackSummary,
        farm_polygon: Sequence[Sequence[float]] | None,
        behavior_label: str = "UNKNOWN",
    ) -> RiskAssessment:
        if not track_summary.trajectory:
            centers = []
            last_center = (0.0, 0.0)
        else:
            centers = [tuple(p["center"]) for p in track_summary.trajectory]
            last_center = centers[-1]

        direction, distance_px = calculate_movement_direction(centers, farm_polygon)
        is_inside = is_point_in_polygon(last_center, farm_polygon) if farm_polygon else False

        return self.engine.calculate_risk(
            species=track_summary.species,
            species_confidence=track_summary.classification_confidence,
            detection_confidence=track_summary.detection_confidence,
            distance_px=distance_px,
            is_inside_farm=is_inside,
            direction=direction,
            average_speed_px_sec=track_summary.average_speed_px_sec,
            duration_seconds=track_summary.duration_seconds,
            behavior=behavior_label,
        )

    def generate_risk_events(
        self,
        tracks: list[TrackSummary],
        behaviors_by_track: dict[int, str],
        farm_polygon: Sequence[Sequence[float]] | None,
    ) -> list[RiskEvent]:
        events: list[RiskEvent] = []
        event_counter = 1

        for track in tracks:
            behavior = behaviors_by_track.get(track.track_id, "UNKNOWN")
            assessment = self.evaluate_track_risk(track, farm_polygon, behavior_label=behavior)

            # Generate risk event for every track, with priority highlight for MODERATE / HIGH / CRITICAL
            events.append(
                RiskEvent(
                    event_id=f"RE-{event_counter:03d}",
                    track_id=track.track_id,
                    species=track.species,
                    timestamp_sec=track.end_time,
                    frame_idx=track.trajectory[-1]["frame_idx"] if track.trajectory else 0,
                    risk_score=assessment.risk_score,
                    risk_level=assessment.risk_level,
                    factors=assessment.factors,
                    confidence=assessment.confidence,
                    distance_image_space=assessment.distance_image_space,
                    direction=assessment.direction,
                    behavior=assessment.behavior,
                )
            )
            event_counter += 1

        return sorted(events, key=lambda e: (e.risk_score, e.timestamp_sec), reverse=True)
