from __future__ import annotations

import abc
import math
from dataclasses import dataclass
from typing import Sequence
import numpy as np

from app.models.tracker import TrajectoryPoint
from app.utils.geometry import DIR_APPROACHING, DIR_INSIDE, DIR_MOVING_AWAY, DIR_STATIONARY
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Observable movement categories
BEH_STATIONARY = "STATIONARY"
BEH_WALKING = "WALKING"
BEH_RUNNING = "RUNNING"
BEH_WANDERING = "WANDERING"
BEH_APPROACHING = "APPROACHING"
BEH_RETREATING = "RETREATING"
BEH_POSSIBLE_RAPID_APPROACH = "POSSIBLE RAPID APPROACH"
BEH_UNKNOWN = "UNKNOWN"


@dataclass
class BehaviorResult:
    behavior: str                   # e.g. "WALKING"
    confidence: float              # 0.0 to 1.0
    observable_factors: list[str]  # e.g. ["Moderate steady pixel speed (24 px/s)", "Consistent directional path"]


class BaseBehaviorModel(abc.ABC):
    """
    Abstract interface for wildlife observable behaviour analysis.
    Designed so that rule-based systems can seamlessly be replaced by
    temporal deep-learning models (LSTM, GRU, or Transformers) in the future.
    """

    @abc.abstractmethod
    def predict(
        self,
        history: Sequence[TrajectoryPoint],
        direction_label: str = "UNKNOWN",
    ) -> BehaviorResult:
        """Predict observable behaviour pattern from track history."""
        pass


class RuleBasedBehaviorModel(BaseBehaviorModel):
    """
    Observable movement pattern analyzer based on trajectory kinematics.
    Strictly observes physical movement (speed, displacement, persistence, heading)
    and makes NO claims regarding animal mental states, intent, or emotion.
    """

    def __init__(
        self,
        stationary_max_speed: float = 8.0,
        walking_max_speed: float = 40.0,
        running_min_speed: float = 40.0,
    ) -> None:
        self.stationary_max_speed = stationary_max_speed
        self.walking_max_speed = walking_max_speed
        self.running_min_speed = running_min_speed

    def predict(
        self,
        history: Sequence[TrajectoryPoint],
        direction_label: str = "UNKNOWN",
    ) -> BehaviorResult:
        if not history or len(history) < 2:
            return BehaviorResult(
                behavior=BEH_UNKNOWN,
                confidence=0.50,
                observable_factors=["Insufficient trajectory frames to classify movement pattern."],
            )

        # Calculate kinematics
        speeds = [p.speed_px_sec for p in history if p.speed_px_sec > 0]
        avg_speed = float(np.mean(speeds)) if speeds else 0.0
        max_speed = float(np.max(speeds)) if speeds else 0.0

        p_start = history[0].center
        p_end = history[-1].center
        displacement = math.hypot(p_end[0] - p_start[0], p_end[1] - p_start[1])

        total_dist = 0.0
        for i in range(1, len(history)):
            total_dist += math.hypot(
                history[i].center[0] - history[i - 1].center[0],
                history[i].center[1] - history[i - 1].center[1],
            )

        # 1. Check for rapid approach toward farm boundary
        if direction_label == DIR_APPROACHING and max_speed >= self.running_min_speed:
            return BehaviorResult(
                behavior=BEH_POSSIBLE_RAPID_APPROACH,
                confidence=0.88,
                observable_factors=[
                    f"Rapid movement observed (peak speed {max_speed:.1f} px/s)",
                    "Trajectory vector points toward farm boundary",
                    f"Net displacement of {displacement:.1f} px toward boundary",
                ],
            )

        # 2. Check for general approaching
        if direction_label in (DIR_APPROACHING, DIR_INSIDE) and avg_speed > self.stationary_max_speed:
            return BehaviorResult(
                behavior=BEH_APPROACHING,
                confidence=0.85,
                observable_factors=[
                    "Trajectory heading toward farm boundary",
                    f"Consistent movement (avg speed {avg_speed:.1f} px/s)",
                ],
            )

        # 3. Check for retreating
        if direction_label == DIR_MOVING_AWAY and avg_speed > self.stationary_max_speed:
            return BehaviorResult(
                behavior=BEH_RETREATING,
                confidence=0.84,
                observable_factors=[
                    "Trajectory heading away from farm boundary",
                    f"Net displacement {displacement:.1f} px away",
                ],
            )

        # 4. Stationary
        if avg_speed <= self.stationary_max_speed and displacement < 15.0:
            return BehaviorResult(
                behavior=BEH_STATIONARY,
                confidence=0.90,
                observable_factors=[
                    f"Minimal displacement ({displacement:.1f} px)",
                    f"Low average pixel speed ({avg_speed:.1f} px/s)",
                ],
            )

        # 5. Running
        if avg_speed >= self.running_min_speed:
            return BehaviorResult(
                behavior=BEH_RUNNING,
                confidence=0.86,
                observable_factors=[
                    f"Elevated movement speed (avg {avg_speed:.1f} px/s, peak {max_speed:.1f} px/s)",
                ],
            )

        # 6. Wandering / meandering
        if total_dist > displacement * 2.2 and displacement < 50.0:
            return BehaviorResult(
                behavior=BEH_WANDERING,
                confidence=0.80,
                observable_factors=[
                    f"Non-linear path with high path-to-displacement ratio ({total_dist / max(1.0, displacement):.1f}x)",
                ],
            )

        # 7. Walking (moderate consistent directional movement)
        return BehaviorResult(
            behavior=BEH_WALKING,
            confidence=0.85,
            observable_factors=[
                f"Steady moderate pixel speed ({avg_speed:.1f} px/s)",
                f"Directional path displacement ({displacement:.1f} px)",
            ],
        )


def get_behavior_model() -> BaseBehaviorModel:
    return RuleBasedBehaviorModel()
