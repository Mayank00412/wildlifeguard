from app.models.behavior_model import (
    BEH_APPROACHING,
    BEH_POSSIBLE_RAPID_APPROACH,
    BEH_RETREATING,
    BEH_RUNNING,
    BEH_STATIONARY,
    BEH_WALKING,
    RuleBasedBehaviorModel,
)
from app.models.tracker import TrajectoryPoint
from app.utils.geometry import DIR_APPROACHING, DIR_MOVING_AWAY


def test_behavior_stationary() -> None:
    model = RuleBasedBehaviorModel()
    history = [
        TrajectoryPoint(frame_idx=0, timestamp_sec=0.0, bbox=[50, 50, 90, 90], center=(70.0, 70.0), speed_px_sec=1.0),
        TrajectoryPoint(frame_idx=1, timestamp_sec=0.5, bbox=[51, 50, 91, 90], center=(71.0, 70.0), speed_px_sec=2.0),
        TrajectoryPoint(frame_idx=2, timestamp_sec=1.0, bbox=[50, 51, 90, 91], center=(70.0, 71.0), speed_px_sec=2.0),
    ]
    res = model.predict(history)
    assert res.behavior == BEH_STATIONARY
    assert res.confidence >= 0.85
    assert len(res.observable_factors) > 0


def test_behavior_walking() -> None:
    model = RuleBasedBehaviorModel()
    history = [
        TrajectoryPoint(frame_idx=0, timestamp_sec=0.0, bbox=[50, 50, 90, 90], center=(70.0, 70.0), speed_px_sec=20.0),
        TrajectoryPoint(frame_idx=1, timestamp_sec=0.5, bbox=[60, 50, 100, 90], center=(80.0, 70.0), speed_px_sec=20.0),
        TrajectoryPoint(frame_idx=2, timestamp_sec=1.0, bbox=[70, 50, 110, 90], center=(90.0, 70.0), speed_px_sec=20.0),
    ]
    res = model.predict(history)
    assert res.behavior == BEH_WALKING


def test_behavior_running() -> None:
    model = RuleBasedBehaviorModel()
    history = [
        TrajectoryPoint(frame_idx=0, timestamp_sec=0.0, bbox=[50, 50, 90, 90], center=(70.0, 70.0), speed_px_sec=65.0),
        TrajectoryPoint(frame_idx=1, timestamp_sec=0.5, bbox=[82, 50, 122, 90], center=(102.0, 70.0), speed_px_sec=64.0),
        TrajectoryPoint(frame_idx=2, timestamp_sec=1.0, bbox=[114, 50, 154, 90], center=(134.0, 70.0), speed_px_sec=64.0),
    ]
    res = model.predict(history)
    assert res.behavior == BEH_RUNNING


def test_behavior_rapid_approach() -> None:
    model = RuleBasedBehaviorModel()
    history = [
        TrajectoryPoint(frame_idx=0, timestamp_sec=0.0, bbox=[50, 50, 90, 90], center=(70.0, 70.0), speed_px_sec=55.0),
        TrajectoryPoint(frame_idx=1, timestamp_sec=0.5, bbox=[80, 50, 120, 90], center=(100.0, 70.0), speed_px_sec=60.0),
    ]
    res = model.predict(history, direction_label=DIR_APPROACHING)
    assert res.behavior == BEH_POSSIBLE_RAPID_APPROACH
    assert "Rapid movement" in res.observable_factors[0]
