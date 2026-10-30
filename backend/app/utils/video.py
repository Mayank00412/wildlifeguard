from __future__ import annotations

from pathlib import Path
from typing import Sequence
import cv2
import numpy as np

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Colors in BGR format
COLOR_GREEN = (46, 204, 113)    # LOW risk
COLOR_YELLOW = (41, 128, 185)   # MODERATE risk (amber/orange)
COLOR_ORANGE = (39, 110, 243)   # HIGH risk
COLOR_RED = (44, 44, 235)       # CRITICAL risk
COLOR_WHITE = (255, 255, 255)
COLOR_DARK = (20, 24, 30)
COLOR_BOUNDARY = (0, 220, 255)  # Cyan boundary line


def get_risk_color(risk_level: str) -> tuple[int, int, int]:
    level = (risk_level or "").upper()
    if level == "CRITICAL":
        return COLOR_RED
    if level == "HIGH":
        return COLOR_ORANGE
    if level == "MODERATE":
        return COLOR_YELLOW
    return COLOR_GREEN


def draw_detection_box(
    frame: np.ndarray,
    bbox: Sequence[float],
    label: str,
    confidence: float,
    color: tuple[int, int, int] = COLOR_GREEN,
    behavior: str | None = None,
    risk_level: str | None = None,
) -> None:
    """Draw high-visibility bounding box and labeled pill badge on frame in-place."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in bbox]
    x1 = max(0, min(w - 1, x1))
    y1 = max(0, min(h - 1, y1))
    x2 = max(0, min(w - 1, x2))
    y2 = max(0, min(h - 1, y2))

    # Bounding rectangle
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

    # Corner accents
    corner_len = min(15, (x2 - x1) // 4, (y2 - y1) // 4)
    if corner_len > 3:
        cv2.line(frame, (x1, y1), (x1 + corner_len, y1), color, 4)
        cv2.line(frame, (x1, y1), (x1, y1 + corner_len), color, 4)
        cv2.line(frame, (x2, y1), (x2 - corner_len, y1), color, 4)
        cv2.line(frame, (x2, y1), (x2, y1 + corner_len), color, 4)
        cv2.line(frame, (x1, y2), (x1 + corner_len, y2), color, 4)
        cv2.line(frame, (x1, y2), (x1, y2 - corner_len), color, 4)
        cv2.line(frame, (x2, y2), (x2 - corner_len, y2), color, 4)
        cv2.line(frame, (x2, y2), (x2, y2 - corner_len), color, 4)

    # Header label: e.g. "Elephant #01 (92%)"
    text = f"{label} ({int(confidence * 100)}%)"
    if behavior:
        text += f" | {behavior}"
    if risk_level:
        text += f" [{risk_level}]"

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.45
    thickness = 1
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)

    badge_y1 = max(0, y1 - th - 10)
    badge_y2 = y1
    badge_x1 = x1
    badge_x2 = min(w, x1 + tw + 12)

    # Semi-transparent background badge
    sub_img = frame[badge_y1:badge_y2, badge_x1:badge_x2]
    if sub_img.shape[0] > 0 and sub_img.shape[1] > 0:
        dark_rect = np.full_like(sub_img, color, dtype=np.uint8)
        blended = cv2.addWeighted(sub_img, 0.25, dark_rect, 0.75, 0)
        frame[badge_y1:badge_y2, badge_x1:badge_x2] = blended

    cv2.putText(
        frame,
        text,
        (badge_x1 + 6, badge_y2 - 5),
        font,
        scale,
        COLOR_WHITE,
        thickness,
        cv2.LINE_AA,
    )


def draw_farm_boundary(
    frame: np.ndarray,
    polygon_points: Sequence[Sequence[float]],
    label: str = "Farm Boundary",
) -> None:
    """Draw farm polygon boundary overlay."""
    if len(polygon_points) < 3:
        return
    pts = np.array(polygon_points, dtype=np.int32).reshape((-1, 1, 2))
    # Draw translucent filled overlay
    overlay = frame.copy()
    cv2.fillPoly(overlay, [pts], (0, 180, 220))
    cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
    # Draw polygon border
    cv2.polylines(frame, [pts], isClosed=True, color=COLOR_BOUNDARY, thickness=2, lineType=cv2.LINE_AA)

    # Add label near first point
    first_pt = pts[0][0]
    cv2.putText(
        frame,
        label,
        (int(first_pt[0]) + 5, int(first_pt[1]) - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        COLOR_BOUNDARY,
        1,
        cv2.LINE_AA,
    )


def create_annotated_video(
    source_video_path: Path,
    output_video_path: Path,
    frame_annotations: dict[int, list[dict]],
    farm_boundary: Sequence[Sequence[float]] | None = None,
    target_fps: int = 15,
) -> bool:
    """Render annotated MP4 video with bounding boxes, risk badges, and boundary."""
    if not source_video_path.exists():
        return False

    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(source_video_path))
    if not cap.isOpened():
        return False

    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)

        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        writer = cv2.VideoWriter(str(output_video_path), fourcc, min(fps, float(target_fps)), (width, height))
        if not writer.isOpened():
            # Fallback codec if avc1 is unavailable
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(output_video_path), fourcc, min(fps, float(target_fps)), (width, height))

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            # Draw farm boundary if present
            if farm_boundary:
                draw_farm_boundary(frame, farm_boundary)

            # Draw any detections for this frame
            items = frame_annotations.get(frame_idx, [])
            for item in items:
                bbox = item.get("bbox", [0, 0, 0, 0])
                label = item.get("label", "Animal")
                conf = float(item.get("confidence", 0.9))
                behavior = item.get("behavior")
                risk_level = item.get("risk_level", "LOW")
                color = get_risk_color(risk_level)
                draw_detection_box(frame, bbox, label, conf, color, behavior, risk_level)

            # Draw overlay timestamp & frame index header
            time_sec = frame_idx / fps if fps > 0 else 0.0
            header_text = f"T: {time_sec:.2f}s | F: {frame_idx}"
            cv2.putText(frame, header_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2, cv2.LINE_AA)
            cv2.putText(frame, header_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 1, cv2.LINE_AA)

            writer.write(frame)
            frame_idx += 1

        writer.release()
        return True
    except Exception as exc:
        logger.error("Failed to render annotated video: %s", exc)
        return False
    finally:
        cap.release()
