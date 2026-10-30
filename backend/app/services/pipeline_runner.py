from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.database import get_session_factory
from app.database.models import Analysis, FarmBoundary, RiskEventRecord, TrackRecord, Video
from app.models.tracker import DetectionInput
from app.services.behavior_service import BehaviorService
from app.services.classification_service import ClassificationService
from app.services.detection_service import DetectionService
from app.services.risk_service import RiskService
from app.services.tracking_service import TrackingService
from app.services.video_processor import VideoProcessor
from app.services.video_storage import VideoStorageService
from app.utils.geometry import calculate_movement_direction, is_point_in_polygon
from app.utils.logging import get_logger
from app.utils.video import create_annotated_video

logger = get_logger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def run_video_analysis_pipeline(
    analysis_id: str,
    video_id: str,
    custom_polygon: Sequence[Sequence[float]] | None = None,
    process_fps: int | None = None,
) -> None:
    """
    Background worker executing the complete end-to-end WildlifeGuard AI pipeline:
    1. Probe video metadata
    2. Extract frames at target_fps
    3. Wildlife detection (MegaDetector V6 / fallback)
    4. Species classification (PyTorch-Wildlife classifier / fallback)
    5. Multi-object tracking & trajectory analysis (ByteIoUTracker)
    6. Farm boundary geometry & movement direction
    7. Observable behaviour analysis
    8. Encounter-risk assessment engine
    9. Annotated video generation
    10. Database persistence
    """
    session_factory = get_session_factory()
    db: Session = session_factory()
    settings = get_settings()

    analysis = db.get(Analysis, analysis_id)
    video = db.get(Video, video_id)
    if not analysis or not video:
        logger.error("Analysis %s or Video %s not found in pipeline worker.", analysis_id, video_id)
        db.close()
        return

    try:
        storage = VideoStorageService(db)
        video_path = storage.resolve_path(video)

        # 1. Probe & extract metadata if not already done
        analysis.status = "PROCESSING"
        analysis.current_stage = "Probing video stream metadata..."
        analysis.progress_percent = 10
        db.commit()

        processor = VideoProcessor(target_fps=process_fps)
        if video.fps is None:
            storage.probe_and_update_metadata(video)

        # 2. Get farm boundary polygon (custom from request, or saved for video)
        polygon: list[list[float]] = []
        if custom_polygon:
            polygon = [list(pt) for pt in custom_polygon]
            # Save or update farm boundary in DB
            existing_boundary = db.query(FarmBoundary).filter(FarmBoundary.video_id == video_id).first()
            if existing_boundary:
                existing_boundary.polygon_json = json.dumps(polygon)
            else:
                db.add(FarmBoundary(video_id=video_id, polygon_json=json.dumps(polygon)))
            db.commit()
        else:
            boundary_rec = db.query(FarmBoundary).filter(FarmBoundary.video_id == video_id).first()
            if boundary_rec:
                try:
                    polygon = json.loads(boundary_rec.polygon_json)
                except Exception:
                    polygon = []

        # 3. Detection & Tracking Frame-by-Frame
        analysis.current_stage = "Detecting wildlife and classifying species..."
        analysis.progress_percent = 25
        db.commit()

        detection_service = DetectionService()
        classification_service = ClassificationService()
        tracking_service = TrackingService()

        # Data structure for annotated video generation: {frame_idx: [detections]}
        frame_annotations: dict[int, list[dict]] = {}
        all_detections_count = 0
        total_frames_processed = 0

        # Sample frames generator
        frames_list: list[tuple[int, float, np.ndarray]] = []
        for f_idx, timestamp_sec, frame in processor.extract_frames(video_path, target_fps=process_fps):
            frames_list.append((f_idx, timestamp_sec, frame))
            total_frames_processed += 1

        total_sample_frames = max(1, len(frames_list))

        for idx, (f_idx, timestamp_sec, frame) in enumerate(frames_list):
            det_result = detection_service.detect_in_frame(frame, frame_idx=f_idx, timestamp_sec=timestamp_sec)
            all_detections_count += len(det_result.detections)

            # Classify species for each detection crop
            tracking_inputs: list[DetectionInput] = []
            for det in det_result.detections:
                species_res = classification_service.classify_detection(frame, det.bbox)
                tracking_inputs.append(
                    DetectionInput(
                        bbox=det.bbox,
                        detection_confidence=det.confidence,
                        species=species_res.species,
                        classification_confidence=species_res.confidence,
                    )
                )

            # Update tracker
            active_tracks = tracking_service.update(tracking_inputs, f_idx, timestamp_sec)

            # Record frame annotations
            items = []
            for trk in active_tracks:
                items.append(
                    {
                        "bbox": trk.bbox,
                        "label": f"{trk.species.replace('_', ' ').title()} #{trk.track_id:02d}",
                        "confidence": trk.detection_confidence,
                        "behavior": "TRACKING",
                        "risk_level": "LOW",
                    }
                )
            frame_annotations[f_idx] = items

            # Update progress incrementally
            if idx % max(1, total_sample_frames // 4) == 0:
                pct = 25 + int((idx / total_sample_frames) * 35)
                analysis.progress_percent = min(60, pct)
                db.commit()

        # 4. Trajectory, Behaviour & Risk Analysis
        analysis.current_stage = "Analyzing movement trajectories, behaviour & encounter risk..."
        analysis.progress_percent = 65
        db.commit()

        track_summaries = tracking_service.get_all_summaries()
        behavior_service = BehaviorService()
        risk_service = RiskService()

        behaviors_by_track: dict[int, str] = {}
        risk_by_track: dict[int, tuple[int, str]] = {}
        direction_by_track: dict[int, str] = {}

        for summary in track_summaries:
            centers = [tuple(p["center"]) for p in summary.trajectory] if summary.trajectory else []
            direction, _ = calculate_movement_direction(centers, polygon)
            direction_by_track[summary.track_id] = direction

            # Mock track state for behavior analysis
            dummy_track = tracking_service.all_completed_tracks.get(summary.track_id)
            if dummy_track:
                beh_res = behavior_service.analyze_behavior(dummy_track, direction_label=direction)
                behaviors_by_track[summary.track_id] = beh_res.behavior
            else:
                behaviors_by_track[summary.track_id] = "UNKNOWN"

            # Encounter-Risk calculation
            risk_res = risk_service.evaluate_track_risk(
                summary,
                polygon,
                behavior_label=behaviors_by_track[summary.track_id],
            )
            risk_by_track[summary.track_id] = (risk_res.risk_score, risk_res.risk_level)

        # Backfill behaviour and risk labels into frame_annotations for annotated video
        for f_idx, items in frame_annotations.items():
            for item in items:
                label_parts = item["label"].split("#")
                if len(label_parts) == 2:
                    try:
                        t_id = int(label_parts[1].split()[0])
                        if t_id in behaviors_by_track:
                            item["behavior"] = behaviors_by_track[t_id]
                        if t_id in risk_by_track:
                            item["risk_level"] = risk_by_track[t_id][1]
                    except ValueError:
                        pass

        # 5. Generate Annotated Video
        analysis.current_stage = "Rendering annotated video visualization..."
        analysis.progress_percent = 78
        db.commit()

        annotated_filename = f"annotated_{analysis_id}.mp4"
        annotated_path = settings.processed_path / video_id / annotated_filename
        success = create_annotated_video(
            source_video_path=video_path,
            output_video_path=annotated_path,
            frame_annotations=frame_annotations,
            farm_boundary=polygon if polygon else None,
            target_fps=processor.target_fps,
        )
        if success:
            analysis.annotated_video_filename = annotated_filename

        # 6. Generate Risk Events and Persist Records
        analysis.current_stage = "Saving risk events and final analytics..."
        analysis.progress_percent = 90
        db.commit()

        risk_events = risk_service.generate_risk_events(track_summaries, behaviors_by_track, polygon)

        # Save Track Records
        for trk in track_summaries:
            risk_score, risk_level = risk_by_track.get(trk.track_id, (0, "LOW"))
            behavior = behaviors_by_track.get(trk.track_id, "UNKNOWN")
            direction = direction_by_track.get(trk.track_id, "UNKNOWN")

            rec = TrackRecord(
                analysis_id=analysis_id,
                track_id=trk.track_id,
                species=trk.species,
                detection_confidence=trk.detection_confidence,
                classification_confidence=trk.classification_confidence,
                duration_seconds=trk.duration_seconds,
                start_time=trk.start_time,
                end_time=trk.end_time,
                average_speed_px_sec=trk.average_speed_px_sec,
                max_speed_px_sec=trk.max_speed_px_sec,
                total_displacement_px=trk.total_displacement_px,
                direction=direction,
                behavior=behavior,
                risk_score=risk_score,
                risk_level=risk_level,
                trajectory_json=json.dumps(trk.trajectory),
            )
            db.add(rec)

        # Save Risk Event Records
        for rev in risk_events:
            event_rec = RiskEventRecord(
                analysis_id=analysis_id,
                track_id=rev.track_id,
                event_code=rev.event_id,
                species=rev.species,
                timestamp_sec=rev.timestamp_sec,
                risk_score=rev.risk_score,
                risk_level=rev.risk_level,
                factors_json=json.dumps(rev.factors),
                confidence=rev.confidence,
                distance_image_space=rev.distance_image_space,
                direction=rev.direction,
                behavior=rev.behavior,
            )
            db.add(event_rec)

        # Aggregate summary statistics
        species_list = list({t.species for t in track_summaries if t.species != "unknown"})
        if not species_list and track_summaries:
            species_list = ["unknown"]

        behavior_dist: dict[str, int] = {}
        for b in behaviors_by_track.values():
            behavior_dist[b] = behavior_dist.get(b, 0) + 1

        risk_dist: dict[str, int] = {}
        for _, lvl in risk_by_track.values():
            risk_dist[lvl] = risk_dist.get(lvl, 0) + 1

        # Max risk level calculation
        risk_priority = {"CRITICAL": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}
        max_level = "LOW"
        for _, lvl in risk_by_track.values():
            if risk_priority.get(lvl, 1) > risk_priority.get(max_level, 1):
                max_level = lvl

        det_confs = [t.detection_confidence for t in track_summaries]
        class_confs = [t.classification_confidence for t in track_summaries if t.classification_confidence > 0]

        analysis.status = "COMPLETED"
        analysis.current_stage = "Analysis completed"
        analysis.progress_percent = 100
        analysis.total_animals = all_detections_count
        analysis.unique_tracks = len(track_summaries)
        analysis.species_detected_json = json.dumps(species_list)
        analysis.avg_detection_confidence = round(float(np.mean(det_confs)), 2) if det_confs else 0.85
        analysis.avg_classification_confidence = round(float(np.mean(class_confs)), 2) if class_confs else 0.80
        analysis.behavior_distribution_json = json.dumps(behavior_dist)
        analysis.risk_distribution_json = json.dumps(risk_dist)
        analysis.max_risk_level = max_level
        analysis.completed_at = utcnow()

        db.commit()
        logger.info("Pipeline completed successfully for video %s (Analysis %s)", video_id, analysis_id)

    except Exception as exc:
        logger.exception("Pipeline failed for video %s: %s", video_id, exc)
        analysis.status = "FAILED"
        analysis.current_stage = f"Analysis failed: {exc}"
        analysis.error_message = str(exc)
        db.commit()
    finally:
        db.close()
