from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class VideoUploadResponse(BaseModel):
    video_id: str
    filename: str
    status: str = "uploaded"


class VideoMetadata(BaseModel):
    video_id: str
    filename: str
    stored_filename: str
    content_type: str | None = None
    size_bytes: int
    status: str
    fps: float | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    total_frames: int | None = None
    processed_fps: int | None = None
    thumbnail_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FrameExtractionResponse(BaseModel):
    video_id: str
    extracted_frames_count: int
    processed_fps: int
    frames_directory: str


class FarmBoundaryCreate(BaseModel):
    polygon: list[list[float]]


class FarmBoundaryResponse(BaseModel):
    video_id: str
    polygon: list[list[float]]


class AnalysisStartRequest(BaseModel):
    farm_boundary: list[list[float]] | None = None
    process_fps: int | None = None


class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    video_id: str
    status: str
    current_stage: str
    progress_percent: int
    error_message: str | None = None


class TrackResponse(BaseModel):
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
    direction: str
    behavior: str
    risk_score: int
    risk_level: str
    trajectory: list[dict] = Field(default_factory=list)


class RiskEventResponse(BaseModel):
    id: str
    event_code: str
    track_id: int
    species: str
    timestamp_sec: float
    risk_score: int
    risk_level: str
    factors: list[str] = Field(default_factory=list)
    confidence: float
    distance_image_space: float
    direction: str
    behavior: str


class AnalysisResultsResponse(BaseModel):
    analysis_id: str
    video_id: str
    status: str
    total_animals: int
    unique_tracks: int
    species_detected: list[str]
    avg_detection_confidence: float
    avg_classification_confidence: float
    behavior_distribution: dict[str, int]
    risk_distribution: dict[str, int]
    max_risk_level: str
    annotated_video_url: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class GlobalTrackResponse(TrackResponse):
    video_id: str
    analysis_id: str
    video_filename: str


class GlobalRiskEventResponse(RiskEventResponse):
    video_id: str
    analysis_id: str
    video_filename: str


class AnalyticsOverviewResponse(BaseModel):
    total_videos: int
    total_analyses: int
    total_animals_detected: int
    total_unique_tracks: int
    high_risk_events_count: int
    species_breakdown: dict[str, int]
    risk_level_breakdown: dict[str, int]
    behavior_breakdown: dict[str, int]


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
    field: str | None = Field(default=None)
