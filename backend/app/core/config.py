from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ALLOWED_VIDEO_EXTENSIONS: Tuple[str, ...] = (".mp4", ".avi", ".mov", ".mkv")
ALLOWED_VIDEO_CONTENT_TYPES: Tuple[str, ...] = (
    "video/mp4",
    "video/x-m4v",
    "video/quicktime",
    "video/x-msvideo",
    "video/avi",
    "video/x-matroska",
    "video/mkv",
    "application/octet-stream",
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "WildlifeGuard"
    app_env: str = "development"
    log_level: str = "INFO"
    demo_mode: bool = True

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "sqlite:///./wildlifeguard.db"

    video_storage_dir: str = "./videos"
    processed_dir: str = "./processed"
    results_dir: str = "./results"
    max_video_size_mb: int = 250

    process_fps: int = 5
    frame_max_width: int = 1280

    model_device: str = "auto"
    detection_model_name: str = "MDV6-yolov10-c"
    detection_confidence: float = 0.35
    classification_model_name: str = ""
    classification_confidence: float = 0.50
    model_weights_dir: str = "./models"

    risk_low_max: int = 25
    risk_moderate_max: int = 50
    risk_high_max: int = 75

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    def resolve_dir(self, value: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @property
    def video_dir(self) -> Path:
        return self.resolve_dir(self.video_storage_dir)

    @property
    def processed_path(self) -> Path:
        return self.resolve_dir(self.processed_dir)

    @property
    def results_path(self) -> Path:
        return self.resolve_dir(self.results_dir)

    @property
    def max_video_size_bytes(self) -> int:
        return self.max_video_size_mb * 1024 * 1024

    @property
    def resolved_database_url(self) -> str:
        url = self.database_url
        prefix = "sqlite:///"
        if url.startswith(prefix) and not url.startswith("sqlite:////"):
            raw = url[len(prefix) :]
            db_path = Path(raw)
            if not db_path.is_absolute():
                db_path = (self.project_root / db_path).resolve()
            return f"sqlite:///{db_path.as_posix()}"
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
