import json
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import FarmBoundary
from app.database.schemas import (
    FarmBoundaryCreate,
    FarmBoundaryResponse,
    FrameExtractionResponse,
    VideoMetadata,
    VideoUploadResponse,
)
from app.services.video_processor import VideoProcessor
from app.services.video_storage import VideoStorageService
from app.utils.files import VideoValidationError

router = APIRouter(prefix="/videos", tags=["videos"])


def _storage(db: Session = Depends(get_db)) -> VideoStorageService:
    return VideoStorageService(db)


def _to_metadata(video, storage: VideoStorageService) -> VideoMetadata:
    thumb_exists = storage.get_thumbnail_path(video.id).exists()
    return VideoMetadata(
        video_id=video.id,
        filename=video.original_filename,
        stored_filename=video.stored_filename,
        content_type=video.content_type,
        size_bytes=video.size_bytes,
        status=video.status,
        fps=video.fps,
        width=video.width,
        height=video.height,
        duration_seconds=video.duration_seconds,
        total_frames=video.total_frames,
        processed_fps=video.processed_fps,
        thumbnail_url=f"/api/videos/{video.id}/thumbnail" if thumb_exists else None,
        created_at=video.created_at,
    )


def _parse_content_length(content_length: str | None) -> int | None:
    if content_length is None:
        return None
    try:
        return int(content_length)
    except ValueError:
        return None


@router.post("/upload", response_model=VideoUploadResponse)
def upload_video(
    file: UploadFile = File(...),
    content_length: str | None = Header(default=None),
    storage: VideoStorageService = Depends(_storage),
) -> VideoUploadResponse:
    try:
        video = storage.save_upload(file, _parse_content_length(content_length))
    except VideoValidationError as exc:
        status_code = 413 if exc.code == "file_too_large" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return VideoUploadResponse(
        video_id=video.id,
        filename=video.original_filename,
        status=video.status,
    )


@router.get("", response_model=list[VideoMetadata])
def list_videos(storage: VideoStorageService = Depends(_storage)) -> list[VideoMetadata]:
    return [_to_metadata(video, storage) for video in storage.list_videos()]


@router.get("/{video_id}", response_model=VideoMetadata)
def get_video(video_id: str, storage: VideoStorageService = Depends(_storage)) -> VideoMetadata:
    video = storage.get(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found.")
    
    # Lazy probe if metadata is missing
    if video.fps is None:
        try:
            video = storage.probe_and_update_metadata(video)
        except Exception:
            pass

    return _to_metadata(video, storage)


@router.delete("/{video_id}")
def delete_video(video_id: str, storage: VideoStorageService = Depends(_storage)) -> dict[str, str]:
    video = storage.get(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found.")
    storage.delete_video(video)
    return {"status": "deleted", "video_id": video_id}


@router.get("/{video_id}/thumbnail")
def get_thumbnail(video_id: str, storage: VideoStorageService = Depends(_storage)) -> FileResponse:
    video = storage.get(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found.")
    thumb_path = storage.get_thumbnail_path(video_id)
    if not thumb_path.exists():
        try:
            storage.probe_and_update_metadata(video)
        except Exception:
            pass
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not available.")
    return FileResponse(path=thumb_path, media_type="image/jpeg", filename=f"{video_id}_thumb.jpg")


@router.post("/{video_id}/extract-frames", response_model=FrameExtractionResponse)
def extract_frames(
    video_id: str,
    target_fps: int | None = None,
    storage: VideoStorageService = Depends(_storage),
) -> FrameExtractionResponse:
    video = storage.get(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found.")
    video_path = storage.resolve_path(video)
    output_dir = storage.settings.processed_path / video_id / "frames"
    processor = VideoProcessor(target_fps=target_fps)
    try:
        saved = processor.extract_and_save_frames(video_path, output_dir, target_fps=target_fps)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Frame extraction failed: {exc}") from exc

    return FrameExtractionResponse(
        video_id=video_id,
        extracted_frames_count=len(saved),
        processed_fps=processor.target_fps,
        frames_directory=str(output_dir),
    )


@router.get("/{video_id}/file")
def download_video(video_id: str, storage: VideoStorageService = Depends(_storage)) -> FileResponse:
    video = storage.get(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found.")
    path = storage.resolve_path(video)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video file is missing on disk.")
    return FileResponse(
        path=path,
        media_type=video.content_type or "application/octet-stream",
        filename=video.original_filename,
    )


@router.post("/{video_id}/boundary", response_model=FarmBoundaryResponse)
def save_farm_boundary(
    video_id: str,
    payload: FarmBoundaryCreate,
    storage: VideoStorageService = Depends(_storage),
) -> FarmBoundaryResponse:
    video = storage.get(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found.")

    existing = storage.db.query(FarmBoundary).filter(FarmBoundary.video_id == video_id).first()
    if existing:
        existing.polygon_json = json.dumps(payload.polygon)
    else:
        existing = FarmBoundary(video_id=video_id, polygon_json=json.dumps(payload.polygon))
        storage.db.add(existing)

    storage.db.commit()
    return FarmBoundaryResponse(video_id=video_id, polygon=payload.polygon)


@router.get("/{video_id}/boundary", response_model=FarmBoundaryResponse)
def get_farm_boundary(
    video_id: str,
    storage: VideoStorageService = Depends(_storage),
) -> FarmBoundaryResponse:
    video = storage.get(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found.")

    existing = storage.db.query(FarmBoundary).filter(FarmBoundary.video_id == video_id).first()
    polygon = json.loads(existing.polygon_json) if existing else []
    return FarmBoundaryResponse(video_id=video_id, polygon=polygon)
