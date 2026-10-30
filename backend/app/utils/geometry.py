from __future__ import annotations

import math
from typing import Sequence
import cv2
import numpy as np

# Direction constants
DIR_APPROACHING = "APPROACHING FARM"
DIR_MOVING_AWAY = "MOVING AWAY"
DIR_PARALLEL = "MOVING PARALLEL"
DIR_STATIONARY = "STATIONARY"
DIR_INSIDE = "INSIDE FARM"
DIR_UNKNOWN = "UNKNOWN"


def is_point_in_polygon(point: tuple[float, float], polygon: Sequence[Sequence[float]]) -> bool:
    """Return True if point (x, y) is inside the polygon."""
    if len(polygon) < 3:
        return False
    pts = np.array(polygon, dtype=np.float32).reshape((-1, 1, 2))
    res = cv2.pointPolygonTest(pts, (float(point[0]), float(point[1])), measureDist=False)
    return res >= 0


def point_to_polygon_distance(point: tuple[float, float], polygon: Sequence[Sequence[float]]) -> float:
    """
    Return shortest Euclidean distance from point to polygon boundary in image-space pixels.
    Positive value indicates absolute image-space distance.
    """
    if len(polygon) < 3:
        return 0.0
    pts = np.array(polygon, dtype=np.float32).reshape((-1, 1, 2))
    # cv2.pointPolygonTest returns signed distance (+ inside, - outside, 0 on edge)
    signed_dist = cv2.pointPolygonTest(pts, (float(point[0]), float(point[1])), measureDist=True)
    return round(abs(float(signed_dist)), 2)


def polygon_centroid(polygon: Sequence[Sequence[float]]) -> tuple[float, float]:
    """Calculate centroid of polygon."""
    pts = np.array(polygon, dtype=np.float32)
    return (float(np.mean(pts[:, 0])), float(np.mean(pts[:, 1])))


def smooth_trajectory_centers(points: Sequence[tuple[float, float]], window: int = 3) -> list[tuple[float, float]]:
    """Moving average filter for trajectory points to suppress detection jitter."""
    if len(points) <= 2 or window <= 1:
        return list(points)
    smoothed: list[tuple[float, float]] = []
    half = window // 2
    for i in range(len(points)):
        start = max(0, i - half)
        end = min(len(points), i + half + 1)
        xs = [p[0] for p in points[start:end]]
        ys = [p[1] for p in points[start:end]]
        smoothed.append((float(np.mean(xs)), float(np.mean(ys))))
    return smoothed


def calculate_movement_direction(
    trajectory_points: Sequence[tuple[float, float]],
    farm_polygon: Sequence[Sequence[float]] | None,
    stationary_threshold_px: float = 6.0,
    approach_delta_px: float = 3.0,
) -> tuple[str, float]:
    """
    Determine movement direction relative to farm polygon boundary.
    Returns (direction_label, current_image_space_distance).
    Direction labels:
    - APPROACHING FARM
    - MOVING AWAY
    - MOVING PARALLEL
    - STATIONARY
    - INSIDE FARM
    - UNKNOWN
    """
    if not trajectory_points:
        return DIR_UNKNOWN, 0.0

    curr_point = trajectory_points[-1]
    if not farm_polygon or len(farm_polygon) < 3:
        # No boundary defined: determine if moving or stationary
        if len(trajectory_points) >= 2:
            p0 = trajectory_points[0]
            dist = math.hypot(curr_point[0] - p0[0], curr_point[1] - p0[1])
            return DIR_STATIONARY if dist < stationary_threshold_px else "MOVING", 0.0
        return DIR_UNKNOWN, 0.0

    current_dist = point_to_polygon_distance(curr_point, farm_polygon)
    inside = is_point_in_polygon(curr_point, farm_polygon)
    if inside:
        return DIR_INSIDE, current_dist

    if len(trajectory_points) < 2:
        return DIR_UNKNOWN, current_dist

    # Apply rolling smoothing to trajectory
    smoothed = smooth_trajectory_centers(trajectory_points, window=min(5, len(trajectory_points)))
    p_start = smoothed[0]
    p_end = smoothed[-1]

    displacement = math.hypot(p_end[0] - p_start[0], p_end[1] - p_start[1])
    if displacement < stationary_threshold_px:
        return DIR_STATIONARY, current_dist

    # Compare boundary distance from start of window to end of window
    dist_start = point_to_polygon_distance(p_start, farm_polygon)
    dist_end = point_to_polygon_distance(p_end, farm_polygon)
    delta = dist_start - dist_end  # Positive if getting closer to farm

    if delta > approach_delta_px:
        return DIR_APPROACHING, current_dist
    elif delta < -approach_delta_px:
        return DIR_MOVING_AWAY, current_dist
    else:
        return DIR_PARALLEL, current_dist
