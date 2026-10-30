from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.models import Video
from app.utils.files import (
    VideoValidationError,
    is_within_directory,
    sanitize_filename,
    validate_content_type,
    validate_size,
    validate_video_extension,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)
CHUNK_SIZE = 1024 * 1024


class VideoStorageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.video_dir = self.settings.video_dir
        self.video_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, upload: UploadFile, declared_size: int | None) -> Video:
        original_name = sanitize_filename(upload.filename)
        extension = validate_video_extension(original_name)
        validate_content_type(upload.content_type)

        max_bytes = self.settings.max_video_size_bytes
        if declared_size is not None:
            validate_size(declared_size, max_bytes)

        video_id = str(uuid.uuid4())
        stored_filename = f"{video_id}{extension}"
        destination = (self.video_dir / stored_filename).resolve()
        if not is_within_directory(destination, self.video_dir):
            raise VideoValidationError("Refusing to write outside the video storage directory.", "unsafe_path")

        bytes_written = 0
        try:
            with destination.open("wb") as buffer:
                while True:
                    chunk = upload.file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise VideoValidationError(
                            f"File exceeds the maximum size of {self.settings.max_video_size_mb} MB.",
                            "file_too_large",
                        )
                    buffer.write(chunk)
            validate_size(bytes_written, max_bytes)
        except Exception:
            if destination.exists():
                destination.unlink(missing_ok=True)
            raise

        record = Video(
            id=video_id,
            original_filename=original_name,
            stored_filename=stored_filename,
            content_type=upload.content_type,
            size_bytes=bytes_written,
            status="uploaded",
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        logger.info("Stored video %s (%s, %s bytes)", video_id, original_name, bytes_written)

        # Attempt to probe metadata and extract thumbnail using OpenCV
        try:
            self.probe_and_update_metadata(record)
        except Exception as exc:
            logger.debug("Could not probe video metadata on upload for %s: %s", video_id, exc)

        return record

    def probe_and_update_metadata(self, video: Video) -> Video:
        from app.services.video_processor import VideoProcessor

        path = self.resolve_path(video)
        processor = VideoProcessor()
        meta = processor.probe_metadata(path)

        video.fps = meta.fps
        video.width = meta.width
        video.height = meta.height
        video.duration_seconds = meta.duration_seconds
        video.total_frames = meta.total_frames
        video.processed_fps = meta.processing_fps

        # Generate thumbnail
        thumb_path = self.get_thumbnail_path(video.id)
        processor.extract_thumbnail(path, thumb_path)

        self.db.commit()
        self.db.refresh(video)
        return video

    def get_thumbnail_path(self, video_id: str) -> Path:
        return self.settings.processed_path / video_id / "thumbnail.jpg"

    def get(self, video_id: str) -> Video | None:
        return self.db.get(Video, video_id)

    def list_videos(self) -> list[Video]:
        return list(self.db.scalars(select(Video).order_by(Video.created_at.desc())).all())

    def resolve_path(self, video: Video) -> Path:
        path = (self.video_dir / video.stored_filename).resolve()
        if not is_within_directory(path, self.video_dir):
            raise VideoValidationError("Stored video path is invalid.", "unsafe_path")
        return path

    def delete_video(self, video: Video) -> None:
        # Remove raw video from videos directory
        try:
            path = self.resolve_path(video)
            if path.exists():
                path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Could not delete video file for %s: %s", video.id, exc)

        # Remove processed folder (frames, thumbnail, annotated video)
        try:
            processed_dir = self.settings.processed_path / video.id
            if processed_dir.exists():
                shutil.rmtree(processed_dir, ignore_errors=True)
        except Exception as exc:
            logger.warning("Could not delete processed files for %s: %s", video.id, exc)

        # Remove database record (cascades deletion to farm boundary, analyses, tracks, events)
        self.db.delete(video)
        self.db.commit()
        logger.info("Deleted video %s and associated pipeline records.", video.id)
