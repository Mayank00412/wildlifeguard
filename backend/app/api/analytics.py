from __future__ import annotations

import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Analysis, RiskEventRecord, TrackRecord, Video
from app.database.schemas import AnalyticsOverviewResponse, GlobalRiskEventResponse, GlobalTrackResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(db: Session = Depends(get_db)) -> AnalyticsOverviewResponse:
    total_videos = db.query(Video).count()
    analyses = db.query(Analysis).all()
    total_analyses = len(analyses)

    total_animals = sum(a.total_animals for a in analyses)
    total_tracks = sum(a.unique_tracks for a in analyses)

    # Count high/critical risk events
    high_risk_count = (
        db.query(RiskEventRecord)
        .filter(RiskEventRecord.risk_level.in_(["HIGH", "CRITICAL"]))
        .count()
    )

    species_breakdown: dict[str, int] = {}
    risk_breakdown: dict[str, int] = {"LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0}
    behavior_breakdown: dict[str, int] = {}

    for a in analyses:
        # Aggregate species
        try:
            sp_list = json.loads(a.species_detected_json or "[]")
            for sp in sp_list:
                species_breakdown[sp] = species_breakdown.get(sp, 0) + 1
        except Exception:
            pass

        # Aggregate risk distribution
        try:
            r_dist = json.loads(a.risk_distribution_json or "{}")
            for k, v in r_dist.items():
                risk_breakdown[k] = risk_breakdown.get(k, 0) + int(v)
        except Exception:
            pass

        # Aggregate behavior distribution
        try:
            b_dist = json.loads(a.behavior_distribution_json or "{}")
            for k, v in b_dist.items():
                behavior_breakdown[k] = behavior_breakdown.get(k, 0) + int(v)
        except Exception:
            pass

    return AnalyticsOverviewResponse(
        total_videos=total_videos,
        total_analyses=total_analyses,
        total_animals_detected=total_animals,
        total_unique_tracks=total_tracks,
        high_risk_events_count=high_risk_count,
        species_breakdown=species_breakdown,
        risk_level_breakdown=risk_breakdown,
        behavior_breakdown=behavior_breakdown,
    )


@router.get("/animals", response_model=list[GlobalTrackResponse])
def list_animals(db: Session = Depends(get_db)) -> list[GlobalTrackResponse]:
    rows = (
        db.query(TrackRecord, Analysis, Video)
        .join(Analysis, TrackRecord.analysis_id == Analysis.id)
        .join(Video, Analysis.video_id == Video.id)
        .order_by(TrackRecord.risk_score.desc())
        .all()
    )
    results: list[GlobalTrackResponse] = []
    for track, analysis, video in rows:
        results.append(
            GlobalTrackResponse(
                track_id=track.track_id,
                species=track.species,
                detection_confidence=track.detection_confidence,
                classification_confidence=track.classification_confidence,
                duration_seconds=track.duration_seconds,
                start_time=track.start_time,
                end_time=track.end_time,
                average_speed_px_sec=track.average_speed_px_sec,
                max_speed_px_sec=track.max_speed_px_sec,
                total_displacement_px=track.total_displacement_px,
                direction=track.direction,
                behavior=track.behavior,
                risk_score=track.risk_score,
                risk_level=track.risk_level,
                trajectory=json.loads(track.trajectory_json or "[]"),
                video_id=video.id,
                analysis_id=analysis.id,
                video_filename=video.original_filename,
            )
        )
    return results


@router.get("/risk-events", response_model=list[GlobalRiskEventResponse])
def list_risk_events(db: Session = Depends(get_db)) -> list[GlobalRiskEventResponse]:
    rows = (
        db.query(RiskEventRecord, Analysis, Video)
        .join(Analysis, RiskEventRecord.analysis_id == Analysis.id)
        .join(Video, Analysis.video_id == Video.id)
        .order_by(RiskEventRecord.risk_score.desc())
        .all()
    )
    results: list[GlobalRiskEventResponse] = []
    for event, analysis, video in rows:
        results.append(
            GlobalRiskEventResponse(
                id=event.id,
                event_code=event.event_code,
                track_id=event.track_id,
                species=event.species,
                timestamp_sec=event.timestamp_sec,
                risk_score=event.risk_score,
                risk_level=event.risk_level,
                factors=json.loads(event.factors_json or "[]"),
                confidence=event.confidence,
                distance_image_space=event.distance_image_space,
                direction=event.direction,
                behavior=event.behavior,
                video_id=video.id,
                analysis_id=analysis.id,
                video_filename=video.original_filename,
            )
        )
    return results
