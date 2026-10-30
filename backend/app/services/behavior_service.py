from __future__ import annotations

from typing import Sequence

from app.models.behavior_model import BaseBehaviorModel, BehaviorResult, get_behavior_model
from app.models.tracker import TrackState, TrajectoryPoint
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BehaviorService:
    """Evaluates observable wildlife movement behavior from track trajectory history."""

    def __init__(self, model: BaseBehaviorModel | None = None) -> None:
        self.model = model or get_behavior_model()

    def analyze_behavior(
        self,
        track: TrackState,
        direction_label: str = "UNKNOWN",
        recent_window: int = 20,
    ) -> BehaviorResult:
        pts = track.history[-recent_window:] if len(track.history) > recent_window else track.history
        return self.model.predict(pts, direction_label=direction_label)
