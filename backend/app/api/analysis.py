from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.database import get_db
from app.database.models import Analysis, FarmBoundary, RiskEventRecord, TrackRecord, Video
from app.database.schemas import (
    AnalysisResultsResponse,
    AnalysisStartRequest,
    AnalysisStatusResponse,
    FarmBoundaryCreate,
    FarmBoundaryResponse,
    RiskEventResponse,
    TrackResponse,
)
from app.services.pipeline_runner import run_video_analysis_pipeline

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/{video_id}/start", response_model=AnalysisStatusResponse)
def start_analysis(
    video_id: str,
    payload: AnalysisStartRequest | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
) -> AnalysisStatusResponse:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    polygon = payload.farm_boundary if payload else None
    process_fps = payload.process_fps if payload else None

    # Create new Analysis record
    analysis = Analysis(
        video_id=video_id,
        status="QUEUED",
        current_stage="Queued for analysis...",
        progress_percent=0,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Launch background processing pipeline
    background_tasks.add_task(
        run_video_analysis_pipeline,
        analysis_id=analysis.id,
        video_id=video_id,
        custom_polygon=polygon,
        process_fps=process_fps,
    )

    return AnalysisStatusResponse(
        analysis_id=analysis.id,
        video_id=video_id,
        status=analysis.status,
        current_stage=analysis.current_stage,
        progress_percent=analysis.progress_percent,
    )


@router.get("/{video_id}/status", response_model=AnalysisStatusResponse)
def get_analysis_status(video_id: str, db: Session = Depends(get_db)) -> AnalysisStatusResponse:
    analysis = (
        db.query(Analysis)
        .filter(Analysis.video_id == video_id)
        .order_by(Analysis.created_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this video.")

    return AnalysisStatusResponse(
        analysis_id=analysis.id,
        video_id=video_id,
        status=analysis.status,
        current_stage=analysis.current_stage,
        progress_percent=analysis.progress_percent,
        error_message=analysis.error_message,
    )


@router.get("/{video_id}/results", response_model=AnalysisResultsResponse)
def get_analysis_results(video_id: str, db: Session = Depends(get_db)) -> AnalysisResultsResponse:
    analysis = (
        db.query(Analysis)
        .filter(Analysis.video_id == video_id)
        .order_by(Analysis.created_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this video.")

    annotated_url = None
    if analysis.annotated_video_filename:
        annotated_url = f"/api/analysis/{video_id}/annotated-video"

    return AnalysisResultsResponse(
        analysis_id=analysis.id,
        video_id=video_id,
        status=analysis.status,
        total_animals=analysis.total_animals,
        unique_tracks=analysis.unique_tracks,
        species_detected=json.loads(analysis.species_detected_json or "[]"),
        avg_detection_confidence=analysis.avg_detection_confidence,
        avg_classification_confidence=analysis.avg_classification_confidence,
        behavior_distribution=json.loads(analysis.behavior_distribution_json or "{}"),
        risk_distribution=json.loads(analysis.risk_distribution_json or "{}"),
        max_risk_level=analysis.max_risk_level,
        annotated_video_url=annotated_url,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
    )


@router.get("/{video_id}/tracks", response_model=list[TrackResponse])
def get_analysis_tracks(video_id: str, db: Session = Depends(get_db)) -> list[TrackResponse]:
    analysis = (
        db.query(Analysis)
        .filter(Analysis.video_id == video_id)
        .order_by(Analysis.created_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this video.")

    tracks = db.query(TrackRecord).filter(TrackRecord.analysis_id == analysis.id).all()
    return [
        TrackResponse(
            track_id=t.track_id,
            species=t.species,
            detection_confidence=t.detection_confidence,
            classification_confidence=t.classification_confidence,
            duration_seconds=t.duration_seconds,
            start_time=t.start_time,
            end_time=t.end_time,
            average_speed_px_sec=t.average_speed_px_sec,
            max_speed_px_sec=t.max_speed_px_sec,
            total_displacement_px=t.total_displacement_px,
            direction=t.direction,
            behavior=t.behavior,
            risk_score=t.risk_score,
            risk_level=t.risk_level,
            trajectory=json.loads(t.trajectory_json or "[]"),
        )
        for t in tracks
    ]


@router.get("/{video_id}/risk-events", response_model=list[RiskEventResponse])
def get_analysis_risk_events(video_id: str, db: Session = Depends(get_db)) -> list[RiskEventResponse]:
    analysis = (
        db.query(Analysis)
        .filter(Analysis.video_id == video_id)
        .order_by(Analysis.created_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this video.")

    events = (
        db.query(RiskEventRecord)
        .filter(RiskEventRecord.analysis_id == analysis.id)
        .order_by(RiskEventRecord.risk_score.desc())
        .all()
    )

    return [
        RiskEventResponse(
            id=e.id,
            event_code=e.event_code,
            track_id=e.track_id,
            species=e.species,
            timestamp_sec=e.timestamp_sec,
            risk_score=e.risk_score,
            risk_level=e.risk_level,
            factors=json.loads(e.factors_json or "[]"),
            confidence=e.confidence,
            distance_image_space=e.distance_image_space,
            direction=e.direction,
            behavior=e.behavior,
        )
        for e in events
    ]


@router.get("/{video_id}/annotated-video")
def get_annotated_video(video_id: str, db: Session = Depends(get_db)) -> FileResponse:
    analysis = (
        db.query(Analysis)
        .filter(Analysis.video_id == video_id, Analysis.status == "COMPLETED")
        .order_by(Analysis.created_at.desc())
        .first()
    )
    if not analysis or not analysis.annotated_video_filename:
        raise HTTPException(status_code=404, detail="Annotated video not found for this analysis.")

    settings = get_settings()
    video_path = settings.processed_path / video_id / analysis.annotated_video_filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Annotated video file is missing on disk.")

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=analysis.annotated_video_filename,
    )


@router.get("/{video_id}/export")
def export_analysis_report(
    video_id: str,
    format: str = "json",
    db: Session = Depends(get_db),
) -> Response:
    analysis = (
        db.query(Analysis)
        .filter(Analysis.video_id == video_id, Analysis.status == "COMPLETED")
        .order_by(Analysis.created_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="No completed analysis found for this video.")

    video = db.get(Video, video_id)
    tracks = db.query(TrackRecord).filter(TrackRecord.analysis_id == analysis.id).all()
    events = (
        db.query(RiskEventRecord)
        .filter(RiskEventRecord.analysis_id == analysis.id)
        .order_by(RiskEventRecord.risk_score.desc())
        .all()
    )

    if format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Record_Type",
            "Track_ID",
            "Event_Code",
            "Species",
            "Timestamp_Sec",
            "Behavior",
            "Direction",
            "Avg_Speed_px_s",
            "Max_Speed_px_s",
            "Displacement_px",
            "Distance_to_Boundary_px",
            "Risk_Score",
            "Risk_Level",
            "Contributing_Factors",
            "Confidence",
        ])

        for t in tracks:
            writer.writerow([
                "TRACK",
                t.track_id,
                "",
                t.species,
                round(t.start_time, 2),
                t.behavior,
                t.direction,
                t.average_speed_px_sec,
                t.max_speed_px_sec,
                t.total_displacement_px,
                "",
                t.risk_score,
                t.risk_level,
                "",
                round(t.detection_confidence, 2),
            ])

        for e in events:
            factors_str = "; ".join(json.loads(e.factors_json or "[]"))
            writer.writerow([
                "RISK_EVENT",
                e.track_id,
                e.event_code,
                e.species,
                round(e.timestamp_sec, 2),
                e.behavior,
                e.direction,
                "",
                "",
                "",
                e.distance_image_space,
                e.risk_score,
                e.risk_level,
                factors_str,
                round(e.confidence, 2),
            ])

        content = output.getvalue()
        filename = f"wildlifeguard_analysis_{video_id[:8]}.csv"
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # JSON export
    data = {
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "video": {
            "video_id": video.id if video else video_id,
            "filename": video.original_filename if video else "unknown",
            "duration_seconds": video.duration_seconds if video else None,
            "fps": video.fps if video else None,
            "resolution": f"{video.width}x{video.height}" if video and video.width else None,
        },
        "summary": {
            "analysis_id": analysis.id,
            "status": analysis.status,
            "total_animals_detected": analysis.total_animals,
            "unique_tracks": analysis.unique_tracks,
            "max_risk_level": analysis.max_risk_level,
            "species_detected": json.loads(analysis.species_detected_json or "[]"),
            "behavior_distribution": json.loads(analysis.behavior_distribution_json or "{}"),
            "risk_distribution": json.loads(analysis.risk_distribution_json or "{}"),
            "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        },
        "tracks": [
            {
                "track_id": t.track_id,
                "species": t.species,
                "behavior": t.behavior,
                "direction": t.direction,
                "duration_seconds": t.duration_seconds,
                "start_time": t.start_time,
                "end_time": t.end_time,
                "average_speed_px_sec": t.average_speed_px_sec,
                "max_speed_px_sec": t.max_speed_px_sec,
                "total_displacement_px": t.total_displacement_px,
                "risk_score": t.risk_score,
                "risk_level": t.risk_level,
                "trajectory": json.loads(t.trajectory_json or "[]"),
            }
            for t in tracks
        ],
        "risk_events": [
            {
                "event_code": e.event_code,
                "track_id": e.track_id,
                "species": e.species,
                "timestamp_sec": e.timestamp_sec,
                "risk_score": e.risk_score,
                "risk_level": e.risk_level,
                "factors": json.loads(e.factors_json or "[]"),
                "distance_image_space": e.distance_image_space,
                "direction": e.direction,
                "behavior": e.behavior,
                "confidence": e.confidence,
            }
            for e in events
        ],
    }
    filename = f"wildlifeguard_analysis_{video_id[:8]}.json"
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
