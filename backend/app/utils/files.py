import re
from pathlib import Path

from app.core.config import ALLOWED_VIDEO_CONTENT_TYPES, ALLOWED_VIDEO_EXTENSIONS

UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class VideoValidationError(ValueError):
    def __init__(self, message: str, code: str = "invalid_video") -> None:
        super().__init__(message)
        self.code = code


def sanitize_filename(filename: str | None) -> str:
    """Return a safe basename with no path components."""
    raw = (filename or "").replace("\\", "/")
    name = Path(raw).name
    if not name or name in {".", ".."}:
        raise VideoValidationError("A valid video filename is required.", "invalid_filename")
    if name.startswith("."):
        raise VideoValidationError("Hidden or extension-only filenames are not allowed.", "invalid_filename")
    cleaned = UNSAFE_FILENAME_CHARS.sub("_", name)
    cleaned = cleaned.strip("._")
    if not cleaned:
        raise VideoValidationError("Filename could not be sanitized.", "invalid_filename")
    return cleaned[:255]


def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_video_extension(filename: str) -> str:
    extension = get_extension(filename)
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        allowed = ", ".join(ALLOWED_VIDEO_EXTENSIONS)
        raise VideoValidationError(
            f"Unsupported video format '{extension or 'unknown'}'. Allowed: {allowed}.",
            "unsupported_format",
        )
    return extension


def validate_content_type(content_type: str | None) -> None:
    if not content_type:
        return
    normalized = content_type.split(";")[0].strip().lower()
    if (
        normalized.startswith("video/")
        or normalized in ALLOWED_VIDEO_CONTENT_TYPES
        or normalized in ("application/octet-stream", "application/x-matroska", "binary/octet-stream")
    ):
        return
    raise VideoValidationError(
        f"Unsupported content type '{content_type}'. Please upload an MP4, AVI, MOV, or MKV video.",
        "unsupported_content_type",
    )


def validate_size(size_bytes: int, max_bytes: int) -> None:
    if size_bytes <= 0:
        raise VideoValidationError("The uploaded file is empty.", "empty_file")
    if size_bytes > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        raise VideoValidationError(
            f"File exceeds the maximum size of {max_mb:.0f} MB.",
            "file_too_large",
        )


def is_within_directory(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False
