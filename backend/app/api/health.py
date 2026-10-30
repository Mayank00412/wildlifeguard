from fastapi import APIRouter

from app.core.config import ALLOWED_VIDEO_EXTENSIONS, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
    }


@router.get("/config")
def public_config() -> dict:
    settings = get_settings()
    return {
        "max_video_size_mb": settings.max_video_size_mb,
        "allowed_extensions": list(ALLOWED_VIDEO_EXTENSIONS),
        "demo_mode": settings.demo_mode,
        "process_fps": settings.process_fps,
        "model_device": settings.model_device,
        "detection_model_name": settings.detection_model_name,
        "detection_confidence": settings.detection_confidence,
        "classification_confidence": settings.classification_confidence,
        "risk_low_max": settings.risk_low_max,
        "risk_moderate_max": settings.risk_moderate_max,
        "risk_high_max": settings.risk_high_max,
    }
