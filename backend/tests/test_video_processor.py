from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database.database import init_db, reset_engine
from app.database.models import Video
from app.database.database import get_session_factory
from app.main import app
from app.services.video_processor import VideoProcessor


def create_synthetic_video(file_path: Path, width: int = 320, height: int = 240, fps: float = 10.0, num_frames: int = 20) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(file_path), fourcc, fps, (width, height))
    for i in range(num_frames):
        # Draw a synthetic colored frame with a moving rectangle
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = (30, 80, 40)
        cv2.rectangle(frame, (10 + i * 5, 20), (50 + i * 5, 80), (0, 200, 100), -1)
        out.write(frame)
    out.release()
    return file_path


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "test.db"
    video_dir = tmp_path / "videos"
    processed_dir = tmp_path / "processed"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("VIDEO_STORAGE_DIR", str(video_dir))
    monkeypatch.setenv("PROCESSED_DIR", str(processed_dir))
    get_settings.cache_clear()
    reset_engine()
    init_db()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()
    reset_engine()


def test_probe_metadata(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mp4"
    create_synthetic_video(video_path, width=320, height=240, fps=10.0, num_frames=30)

    processor = VideoProcessor(target_fps=5)
    meta = processor.probe_metadata(video_path)

    assert meta.width == 320
    assert meta.height == 240
    assert meta.fps == 10.0
    assert meta.total_frames == 30
    assert meta.duration_seconds == 3.0
    assert meta.processing_fps == 5


def test_extract_frames_sampling(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mp4"
    # 20 frames at 10 fps = 2.0 seconds. target_fps=5 -> step size is 2, expecting 10 sampled frames
    create_synthetic_video(video_path, width=320, height=240, fps=10.0, num_frames=20)

    processor = VideoProcessor(target_fps=5)
    frames = list(processor.extract_frames(video_path))
    assert len(frames) == 10

    # Each item is (frame_idx, timestamp_sec, frame_bgr)
    assert frames[0][0] == 0
    assert frames[0][1] == 0.0
    assert isinstance(frames[0][2], np.ndarray)


def test_extract_frames_max_width_resizing(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mp4"
    create_synthetic_video(video_path, width=400, height=300, fps=10.0, num_frames=10)

    processor = VideoProcessor(target_fps=10, max_width=200)
    frames = list(processor.extract_frames(video_path))
    assert len(frames) == 10
    assert frames[0][2].shape[1] == 200
    assert frames[0][2].shape[0] == 150


def test_extract_thumbnail(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mp4"
    thumb_path = tmp_path / "thumb.jpg"
    create_synthetic_video(video_path, width=320, height=240, fps=10.0, num_frames=15)

    processor = VideoProcessor()
    success = processor.extract_thumbnail(video_path, thumb_path)
    assert success is True
    assert thumb_path.exists()
    assert thumb_path.stat().st_size > 0


def test_extract_and_save_frames(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mp4"
    output_dir = tmp_path / "saved_frames"
    create_synthetic_video(video_path, width=320, height=240, fps=10.0, num_frames=20)

    processor = VideoProcessor(target_fps=5)
    saved = processor.extract_and_save_frames(video_path, output_dir)
    assert len(saved) == 10
    for p in saved:
        assert p.exists()


def test_api_video_metadata_and_extract_frames(client: TestClient, tmp_path: Path) -> None:
    # 1. Create and upload synthetic video
    video_file = tmp_path / "elephant_clip.mp4"
    create_synthetic_video(video_file, width=320, height=240, fps=10.0, num_frames=20)

    with video_file.open("rb") as f:
        resp = client.post("/api/videos/upload", files={"file": ("elephant_clip.mp4", f, "video/mp4")})
    assert resp.status_code == 200
    video_id = resp.json()["video_id"]

    # 2. Get video metadata via GET /api/videos/{video_id}
    meta_resp = client.get(f"/api/videos/{video_id}")
    assert meta_resp.status_code == 200
    meta = meta_resp.json()
    assert meta["width"] == 320
    assert meta["height"] == 240
    assert meta["fps"] == 10.0
    assert meta["total_frames"] == 20
    assert meta["duration_seconds"] == 2.0
    assert meta["thumbnail_url"] is not None

    # 3. Get thumbnail via GET /api/videos/{video_id}/thumbnail
    thumb_resp = client.get(f"/api/videos/{video_id}/thumbnail")
    assert thumb_resp.status_code == 200
    assert thumb_resp.headers["content-type"] == "image/jpeg"

    # 4. Extract frames via POST /api/videos/{video_id}/extract-frames
    extract_resp = client.post(f"/api/videos/{video_id}/extract-frames?target_fps=5")
    assert extract_resp.status_code == 200
    extract_data = extract_resp.json()
    assert extract_data["extracted_frames_count"] == 10
    assert extract_data["processed_fps"] == 5
