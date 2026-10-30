import pytest
from app.utils.geometry import (
    DIR_APPROACHING,
    DIR_INSIDE,
    DIR_MOVING_AWAY,
    DIR_PARALLEL,
    DIR_STATIONARY,
    calculate_movement_direction,
    is_point_in_polygon,
    point_to_polygon_distance,
    polygon_centroid,
)

FARM_POLYGON = [
    [100.0, 100.0],
    [400.0, 100.0],
    [400.0, 400.0],
    [100.0, 400.0],
]


def test_is_point_in_polygon() -> None:
    # Inside farm boundary
    assert is_point_in_polygon((250.0, 250.0), FARM_POLYGON) is True
    # Outside farm boundary
    assert is_point_in_polygon((50.0, 50.0), FARM_POLYGON) is False
    assert is_point_in_polygon((500.0, 250.0), FARM_POLYGON) is False


def test_point_to_polygon_distance() -> None:
    # Point at (50, 250) is 50 px left of line x=100
    dist = point_to_polygon_distance((50.0, 250.0), FARM_POLYGON)
    assert pytest.approx(dist, abs=1.0) == 50.0

    # Point on vertex (100, 100)
    dist_vertex = point_to_polygon_distance((100.0, 100.0), FARM_POLYGON)
    assert pytest.approx(dist_vertex, abs=0.5) == 0.0


def test_polygon_centroid() -> None:
    cx, cy = polygon_centroid(FARM_POLYGON)
    assert cx == 250.0
    assert cy == 250.0


def test_direction_approaching_farm() -> None:
    # Moving from (20, 250) toward farm at x=100: (20,250) -> (40,250) -> (60,250) -> (80,250)
    trajectory = [(20.0, 250.0), (40.0, 250.0), (60.0, 250.0), (80.0, 250.0)]
    direction, dist = calculate_movement_direction(trajectory, FARM_POLYGON)
    assert direction == DIR_APPROACHING
    assert dist < 30.0


def test_direction_moving_away_from_farm() -> None:
    # Moving away from x=100 leftwards: (80, 250) -> (60, 250) -> (40, 250) -> (20, 250)
    trajectory = [(80.0, 250.0), (60.0, 250.0), (40.0, 250.0), (20.0, 250.0)]
    direction, dist = calculate_movement_direction(trajectory, FARM_POLYGON)
    assert direction == DIR_MOVING_AWAY
    assert dist > 70.0


def test_direction_parallel_to_farm() -> None:
    # Moving along y-axis at constant distance x=50: (50, 150) -> (50, 200) -> (50, 250) -> (50, 300)
    trajectory = [(50.0, 150.0), (50.0, 200.0), (50.0, 250.0), (50.0, 300.0)]
    direction, dist = calculate_movement_direction(trajectory, FARM_POLYGON)
    assert direction == DIR_PARALLEL
    assert pytest.approx(dist, abs=1.0) == 50.0


def test_direction_stationary() -> None:
    # Very minor jitter in position
    trajectory = [(50.0, 250.0), (51.0, 250.5), (50.5, 250.0), (50.0, 251.0)]
    direction, _ = calculate_movement_direction(trajectory, FARM_POLYGON)
    assert direction == DIR_STATIONARY


def test_direction_inside_farm() -> None:
    # Points inside farm polygon
    trajectory = [(200.0, 200.0), (210.0, 210.0), (220.0, 220.0)]
    direction, _ = calculate_movement_direction(trajectory, FARM_POLYGON)
    assert direction == DIR_INSIDE
