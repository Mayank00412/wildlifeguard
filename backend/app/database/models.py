from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_frames: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_fps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    farm_boundary: Mapped[FarmBoundary | None] = relationship(
        "FarmBoundary", back_populates="video", uselist=False, cascade="all, delete-orphan"
    )
    analyses: Mapped[list[Analysis]] = relationship(
        "Analysis", back_populates="video", cascade="all, delete-orphan"
    )


class FarmBoundary(Base):
    __tablename__ = "farm_boundaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), unique=True)
    polygon_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    video: Mapped[Video] = relationship("Video", back_populates="farm_boundary")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")  # QUEUED, PROCESSING, COMPLETED, FAILED
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False, default="Queued for analysis...")
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_animals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_tracks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    species_detected_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    avg_detection_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_classification_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    behavior_distribution_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    risk_distribution_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    max_risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="LOW")
    annotated_video_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    video: Mapped[Video] = relationship("Video", back_populates="analyses")
    tracks: Mapped[list[TrackRecord]] = relationship(
        "TrackRecord", back_populates="analysis", cascade="all, delete-orphan"
    )
    risk_events: Mapped[list[RiskEventRecord]] = relationship(
        "RiskEventRecord", back_populates="analysis", cascade="all, delete-orphan"
    )


class TrackRecord(Base):
    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"))
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)
    species: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    detection_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    classification_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    start_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    end_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_speed_px_sec: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_speed_px_sec: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_displacement_px: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    direction: Mapped[str] = mapped_column(String(64), nullable=False, default="UNKNOWN")
    behavior: Mapped[str] = mapped_column(String(64), nullable=False, default="UNKNOWN")
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="LOW")
    trajectory_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    analysis: Mapped[Analysis] = relationship("Analysis", back_populates="tracks")


class RiskEventRecord(Base):
    __tablename__ = "risk_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"))
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_code: Mapped[str] = mapped_column(String(32), nullable=False)
    species: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp_sec: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    factors_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    distance_image_space: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    direction: Mapped[str] = mapped_column(String(64), nullable=False)
    behavior: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship("Analysis", back_populates="risk_events")
