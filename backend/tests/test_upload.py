from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database.database import init_db, reset_engine
from app.main import app
from app.utils.files import sanitize_filename, validate_video_extension
from app.utils.files import VideoValidationError


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "test.db"
    video_dir = tmp_path / "videos"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("VIDEO_STORAGE_DIR", str(video_dir))
    monkeypatch.setenv("MAX_VIDEO_SIZE_MB", "1")
    get_settings.cache_clear()
    reset_engine()
    init_db()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()
    reset_engine()


def test_sanitize_filename_strips_path_traversal() -> None:
    assert sanitize_filename("..\\..\\secret.mp4") == "secret.mp4"
    assert sanitize_filename("/etc/passwd.mp4") == "passwd.mp4"
    with pytest.raises(VideoValidationError):
        sanitize_filename("../..")


def test_validate_video_extension() -> None:
    assert validate_video_extension("clip.MOV") == ".mov"
    with pytest.raises(VideoValidationError):
        validate_video_extension("notes.txt")


def test_upload_valid_mp4(client: TestClient, tmp_path: Path) -> None:
    payload = b"\x00\x00\x00\x18ftypmp42" + b"0" * 128
    response = client.post(
        "/api/videos/upload",
        files={"file": ("elephant.mp4", BytesIO(payload), "video/mp4")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "elephant.mp4"
    assert body["status"] == "uploaded"
    assert body["video_id"]

    stored = list((tmp_path / "videos").glob("*.mp4"))
    assert len(stored) == 1
    assert stored[0].name.startswith(body["video_id"])

    meta = client.get(f"/api/videos/{body['video_id']}")
    assert meta.status_code == 200
    assert meta.json()["filename"] == "elephant.mp4"


def test_upload_rejects_unsupported_extension(client: TestClient) -> None:
    response = client.post(
        "/api/videos/upload",
        files={"file": ("notes.txt", BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported video format" in response.json()["detail"]


def test_upload_rejects_path_traversal_name(client: TestClient) -> None:
    response = client.post(
        "/api/videos/upload",
        files={"file": ("../../evil.mp4", BytesIO(b"video-bytes"), "video/mp4")},
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "evil.mp4"


def test_upload_rejects_oversized_file(client: TestClient) -> None:
    huge = b"0" * (2 * 1024 * 1024)
    response = client.post(
        "/api/videos/upload",
        files={"file": ("big.mp4", BytesIO(huge), "video/mp4")},
    )
    assert response.status_code == 413


def test_delete_video(client: TestClient, tmp_path: Path) -> None:
    payload = b"\x00\x00\x00\x18ftypmp42" + b"0" * 128
    upload_res = client.post(
        "/api/videos/upload",
        files={"file": ("to_delete.mp4", BytesIO(payload), "video/mp4")},
    )
    assert upload_res.status_code == 200
    v_id = upload_res.json()["video_id"]

    # Verify exists
    assert client.get(f"/api/videos/{v_id}").status_code == 200

    # Delete video
    del_res = client.delete(f"/api/videos/{v_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify 404
    assert client.get(f"/api/videos/{v_id}").status_code == 404
