from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database.database import init_db, reset_engine
from app.main import app
from app.services.pipeline_runner import run_video_analysis_pipeline


def create_synthetic_wildlife_video(file_path: Path, width: int = 320, height: int = 240, fps: float = 10.0, num_frames: int = 15) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(file_path), fourcc, fps, (width, height))
    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = (35, 60, 40)
        # Moving wildlife box
        x = 30 + i * 8
        y = 50 + i * 2
        cv2.rectangle(frame, (x, y), (x + 50, y + 40), (80, 140, 90), -1)
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
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()
    reset_engine()
    init_db()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()
    reset_engine()


def test_full_analysis_workflow(client: TestClient, tmp_path: Path) -> None:
    # 1. Create and upload video
    video_file = tmp_path / "elephant_field.mp4"
    create_synthetic_wildlife_video(video_file, width=320, height=240, fps=10.0, num_frames=15)

    with video_file.open("rb") as f:
        upload_resp = client.post("/api/videos/upload", files={"file": ("elephant_field.mp4", f, "video/mp4")})
    assert upload_resp.status_code == 200
    video_id = upload_resp.json()["video_id"]

    # 2. Set farm boundary polygon
    boundary_polygon = [[10.0, 10.0], [150.0, 10.0], [150.0, 200.0], [10.0, 200.0]]
    boundary_resp = client.post(f"/api/videos/{video_id}/boundary", json={"polygon": boundary_polygon})
    assert boundary_resp.status_code == 200
    assert boundary_resp.json()["polygon"] == boundary_polygon

    # Check GET boundary
    get_b_resp = client.get(f"/api/videos/{video_id}/boundary")
    assert get_b_resp.status_code == 200
    assert len(get_b_resp.json()["polygon"]) == 4

    # 3. Start analysis
    start_resp = client.post(f"/api/analysis/{video_id}/start", json={"farm_boundary": boundary_polygon, "process_fps": 5})
    assert start_resp.status_code == 200
    analysis_id = start_resp.json()["analysis_id"]
    assert start_resp.json()["status"] in ("QUEUED", "PROCESSING", "COMPLETED")

    # Run the pipeline synchronously to test completion
    run_video_analysis_pipeline(analysis_id, video_id, custom_polygon=boundary_polygon, process_fps=5)

    # 4. Check analysis status
    status_resp = client.get(f"/api/analysis/{video_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "COMPLETED"
    assert status_resp.json()["progress_percent"] == 100

    # 5. Check analysis results
    results_resp = client.get(f"/api/analysis/{video_id}/results")
    assert results_resp.status_code == 200
    res = results_resp.json()
    assert res["status"] == "COMPLETED"
    assert res["unique_tracks"] >= 1
    assert res["annotated_video_url"] is not None

    # 6. Check tracks endpoint
    tracks_resp = client.get(f"/api/analysis/{video_id}/tracks")
    assert tracks_resp.status_code == 200
    tracks = tracks_resp.json()
    assert len(tracks) >= 1
    t = tracks[0]
    assert t["track_id"] >= 1
    assert t["direction"] != ""
    assert t["behavior"] != ""
    assert len(t["trajectory"]) >= 1

    # 7. Check risk-events endpoint
    events_resp = client.get(f"/api/analysis/{video_id}/risk-events")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 1
    assert events[0]["risk_level"] in ("LOW", "MODERATE", "HIGH", "CRITICAL")
    assert len(events[0]["factors"]) > 0

    # 8. Check annotated video streaming endpoint
    annotated_resp = client.get(f"/api/analysis/{video_id}/annotated-video")
    assert annotated_resp.status_code == 200
    assert annotated_resp.headers["content-type"] == "video/mp4"

    # 9. Check analytics overview
    analytics_resp = client.get("/api/analytics/overview")
    assert analytics_resp.status_code == 200
    overview = analytics_resp.json()
    assert overview["total_videos"] >= 1
    assert overview["total_analyses"] >= 1
    assert overview["total_unique_tracks"] >= 1

    animals_resp = client.get("/api/analytics/animals")
    assert animals_resp.status_code == 200
    assert len(animals_resp.json()) >= 1
    assert animals_resp.json()[0]["video_id"] == video_id

    global_events = client.get("/api/analytics/risk-events")
    assert global_events.status_code == 200
    assert len(global_events.json()) >= 1
    assert global_events.json()[0]["video_filename"] == "elephant_field.mp4"

    # 10. Check export endpoints (CSV and JSON)
    export_json = client.get(f"/api/analysis/{video_id}/export?format=json")
    assert export_json.status_code == 200
    assert "application/json" in export_json.headers["content-type"]
    json_data = export_json.json()
    assert "summary" in json_data
    assert "tracks" in json_data
    assert "risk_events" in json_data

    export_csv = client.get(f"/api/analysis/{video_id}/export?format=csv")
    assert export_csv.status_code == 200
    assert "text/csv" in export_csv.headers["content-type"]
    assert "Track_ID" in export_csv.text
    assert "RISK_EVENT" in export_csv.text
