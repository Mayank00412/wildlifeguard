import pytest
from app.models.tracker import ByteIoUTracker, DetectionInput, compute_iou
from app.services.tracking_service import TrackingService


def test_compute_iou() -> None:
    boxA = [10.0, 10.0, 50.0, 50.0]
    boxB = [10.0, 10.0, 50.0, 50.0]
    assert compute_iou(boxA, boxB) == 1.0

    boxC = [100.0, 100.0, 150.0, 150.0]
    assert compute_iou(boxA, boxC) == 0.0

    # Half overlap
    boxD = [10.0, 10.0, 30.0, 50.0]
    iou = compute_iou(boxA, boxD)
    assert 0.4 < iou < 0.6


def test_tracker_maintains_persistent_id() -> None:
    service = TrackingService(ByteIoUTracker(iou_threshold=0.2))

    # Frame 0: One animal appears
    dets_f0 = [DetectionInput(bbox=[100.0, 100.0, 160.0, 160.0], detection_confidence=0.92, species="elephant", classification_confidence=0.88)]
    tracks_f0 = service.update(dets_f0, frame_idx=0, timestamp_sec=0.0)
    assert len(tracks_f0) == 1
    t1_id = tracks_f0[0].track_id

    # Frame 1: Animal moved slightly
    dets_f1 = [DetectionInput(bbox=[105.0, 102.0, 165.0, 162.0], detection_confidence=0.91, species="elephant", classification_confidence=0.89)]
    tracks_f1 = service.update(dets_f1, frame_idx=1, timestamp_sec=0.2)
    assert len(tracks_f1) == 1
    assert tracks_f1[0].track_id == t1_id
    assert tracks_f1[0].species == "elephant"

    # Frame 2: Second animal appears
    dets_f2 = [
        DetectionInput(bbox=[110.0, 105.0, 170.0, 165.0], detection_confidence=0.90, species="elephant", classification_confidence=0.88),
        DetectionInput(bbox=[300.0, 300.0, 350.0, 350.0], detection_confidence=0.85, species="deer", classification_confidence=0.80),
    ]
    tracks_f2 = service.update(dets_f2, frame_idx=2, timestamp_sec=0.4)
    assert len(tracks_f2) == 2
    track_ids = {t.track_id for t in tracks_f2}
    assert t1_id in track_ids
    assert len(track_ids) == 2


def test_track_trajectory_summary() -> None:
    service = TrackingService()
    # 5 frames moving at ~50 pixels per second
    for i in range(5):
        t_sec = i * 0.2
        x = 50.0 + i * 10.0
        service.update(
            [DetectionInput(bbox=[x, 100.0, x + 40.0, 140.0], detection_confidence=0.9, species="elephant", classification_confidence=0.85)],
            frame_idx=i,
            timestamp_sec=t_sec,
        )

    summaries = service.get_all_summaries()
    assert len(summaries) == 1
    s = summaries[0]
    assert s.species == "elephant"
    assert s.duration_seconds == pytest.approx(0.8, abs=0.1)
    assert s.total_displacement_px == pytest.approx(40.0, abs=1.0)
    assert s.average_speed_px_sec > 40.0
