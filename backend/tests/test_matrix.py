"""Tests for OpenRouteService distance matrix parsing, validation, dimensions, ordering, and offline mode."""

from __future__ import annotations

import io
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

from app.planner.matrix import (
    fetch_ors_matrix,
    get_or_fetch_matrix,
    load_matrix,
    save_matrix,
    validate_matrix_against_monuments,
)
from app.planner.models import (
    MatrixDimensionError,
    MatrixError,
    MatrixOrderError,
    MissingRouteError,
    ORSAPIError,
    TravelMatrix,
)


@pytest.fixture
def mock_monuments() -> list[dict]:
    """Sample list of 3 monuments."""
    return [
        {"slug": "humayuns-tomb", "name": "Humayun's Tomb", "latitude": 28.59333, "longitude": 77.25083, "city": "Delhi"},
        {"slug": "purana-qila", "name": "Purana Qila", "latitude": 28.60944, "longitude": 77.24361, "city": "Delhi"},
        {"slug": "taj-mahal", "name": "Taj Mahal", "latitude": 27.17417, "longitude": 78.04222, "city": "Agra"},
    ]


@pytest.fixture
def valid_matrix(mock_monuments: list[dict]) -> TravelMatrix:
    """A valid 3x3 travel matrix."""
    slugs = [m["slug"] for m in mock_monuments]
    locations = [[m["longitude"], m["latitude"]] for m in mock_monuments]
    durations = [
        [0.0, 360.0, 11000.0],
        [360.0, 0.0, 11200.0],
        [11000.0, 11200.0, 0.0],
    ]
    distances = [
        [0.0, 2500.0, 220000.0],
        [2500.0, 0.0, 222000.0],
        [220000.0, 222000.0, 0.0],
    ]
    matrix = TravelMatrix(
        profile="driving-car",
        monument_slugs=slugs,
        locations=locations,
        durations=durations,
        distances=distances,
        created_at="2026-11-02T16:00:00Z",
        source="openrouteservice",
    )
    matrix.validate()
    return matrix


def test_matrix_parsing_and_metrics(valid_matrix: TravelMatrix):
    """Verify matrix metric calculations, self-loop 0, and minute conversions."""
    assert valid_matrix.get_travel_time_seconds("humayuns-tomb", "humayuns-tomb") == 0.0
    assert valid_matrix.get_travel_time_seconds("humayuns-tomb", "purana-qila") == 360.0
    assert valid_matrix.get_travel_time_minutes("humayuns-tomb", "purana-qila") == 6.0
    assert valid_matrix.get_travel_distance_meters("humayuns-tomb", "purana-qila") == 2500.0
    assert valid_matrix.has_route("humayuns-tomb", "taj-mahal") is True


def test_matrix_dimension_validation(valid_matrix: TravelMatrix):
    """Verify dimension errors are caught when matrix is not NxN."""
    # Fewer rows than slugs
    invalid_durations = valid_matrix.durations[:2]
    bad_matrix = TravelMatrix(
        profile="driving-car",
        monument_slugs=valid_matrix.monument_slugs,
        locations=valid_matrix.locations,
        durations=invalid_durations,
        distances=valid_matrix.distances,
        created_at="2026-11-02T16:00:00Z",
    )
    with pytest.raises(MatrixDimensionError, match="must be 3x3"):
        bad_matrix.validate()

    # Column count mismatch
    bad_distances = [[0.0, 100.0], [100.0, 0.0], [200.0, 200.0]]
    bad_matrix2 = TravelMatrix(
        profile="driving-car",
        monument_slugs=valid_matrix.monument_slugs,
        locations=valid_matrix.locations,
        durations=valid_matrix.durations,
        distances=bad_distances,
        created_at="2026-11-02T16:00:00Z",
    )
    with pytest.raises(MatrixDimensionError, match="must be 3x3"):
        bad_matrix2.validate()


def test_matrix_order_validation(valid_matrix: TravelMatrix, mock_monuments: list[dict]):
    """Verify coordinate ordering against database monuments."""
    validate_matrix_against_monuments(valid_matrix, mock_monuments)

    # Shuffled monuments ordering should raise MatrixOrderError
    shuffled = [mock_monuments[1], mock_monuments[0], mock_monuments[2]]
    with pytest.raises(MatrixOrderError, match="ordering does not match"):
        validate_matrix_against_monuments(valid_matrix, shuffled)

    # Swapped coordinates in monuments
    tampered = [dict(m) for m in mock_monuments]
    tampered[0]["longitude"] = 78.9999
    with pytest.raises(MatrixOrderError, match="Coordinate mismatch"):
        validate_matrix_against_monuments(valid_matrix, tampered)


def test_missing_route_never_fabricates_distances(mock_monuments: list[dict]):
    """Missing or None routes must raise MissingRouteError, never invent fake numbers."""
    slugs = [m["slug"] for m in mock_monuments]
    locations = [[m["longitude"], m["latitude"]] for m in mock_monuments]
    durations = [
        [0.0, 300.0, None],  # No walking route to Taj Mahal
        [300.0, 0.0, None],
        [None, None, 0.0],
    ]
    distances = [
        [0.0, 1000.0, None],
        [1000.0, 0.0, None],
        [None, None, 0.0],
    ]
    matrix = TravelMatrix(
        profile="foot-walking",
        monument_slugs=slugs,
        locations=locations,
        durations=durations,
        distances=distances,
        created_at="2026-11-02T16:00:00Z",
    )
    matrix.validate()

    assert matrix.has_route("humayuns-tomb", "purana-qila") is True
    assert matrix.has_route("humayuns-tomb", "taj-mahal") is False

    with pytest.raises(MissingRouteError, match="No travel route exists"):
        matrix.get_travel_time_seconds("humayuns-tomb", "taj-mahal")

    with pytest.raises(MissingRouteError, match="No travel route exists"):
        matrix.get_travel_distance_meters("humayuns-tomb", "taj-mahal")


def test_invalid_negative_and_nonzero_diagonal(valid_matrix: TravelMatrix):
    """Verify negative numbers and non-zero diagonals are rejected."""
    # Non-zero diagonal
    bad_dur = [list(r) for r in valid_matrix.durations]
    bad_dur[0][0] = 50.0
    m1 = TravelMatrix(
        profile="driving-car",
        monument_slugs=valid_matrix.monument_slugs,
        locations=valid_matrix.locations,
        durations=bad_dur,
        distances=valid_matrix.distances,
        created_at="2026-11-02T16:00:00Z",
    )
    with pytest.raises(MatrixError, match="Diagonal entry .* must be 0"):
        m1.validate()

    # Negative duration
    bad_dur2 = [list(r) for r in valid_matrix.durations]
    bad_dur2[0][1] = -10.0
    m2 = TravelMatrix(
        profile="driving-car",
        monument_slugs=valid_matrix.monument_slugs,
        locations=valid_matrix.locations,
        durations=bad_dur2,
        distances=valid_matrix.distances,
        created_at="2026-11-02T16:00:00Z",
    )
    with pytest.raises(MatrixError, match="Negative duration"):
        m2.validate()


def test_matrix_persistence_roundtrip(valid_matrix: TravelMatrix, tmp_path: Path):
    """Test saving and reloading matrix from disk."""
    out_file = tmp_path / "matrix" / "test_matrix.json"
    save_matrix(valid_matrix, path=out_file)
    assert out_file.is_file()

    loaded = load_matrix(path=out_file)
    assert loaded.profile == valid_matrix.profile
    assert loaded.monument_slugs == valid_matrix.monument_slugs
    assert loaded.durations == valid_matrix.durations
    assert loaded.distances == valid_matrix.distances


def test_offline_mode_loads_without_api_key(valid_matrix: TravelMatrix, tmp_path: Path):
    """Verify offline mode loads local matrix even with no API key and no network calls."""
    out_file = tmp_path / "offline_matrix.json"
    save_matrix(valid_matrix, path=out_file)

    with patch.dict("os.environ", {}, clear=True):
        matrix = get_or_fetch_matrix(
            profile="driving-car",
            offline=True,
            cache_path=out_file,
            api_key="",
        )
        assert matrix.monument_slugs == valid_matrix.monument_slugs


def test_ors_api_error_handling(mock_monuments: list[dict]):
    """Verify ORS API error codes are properly caught and translated."""
    # Missing API key
    with pytest.raises(ORSAPIError, match="ORS_API_KEY environment variable is not set"):
        fetch_ors_matrix(mock_monuments, api_key="")

    # Mock 401 Unauthorized
    http_error_401 = urllib.error.HTTPError(
        url="https://api.openrouteservice.org",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=io.BytesIO(b'{"error": "Unauthorized"}'),
    )
    with (
        patch("urllib.request.urlopen", side_effect=http_error_401),
        pytest.raises(ORSAPIError, match="Authentication failed"),
    ):
        fetch_ors_matrix(mock_monuments, api_key="invalid-key")

    # Mock 429 Rate Limit
    http_error_429 = urllib.error.HTTPError(
        url="https://api.openrouteservice.org",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=io.BytesIO(b'{"error": "Rate limit exceeded"}'),
    )
    with (
        patch("urllib.request.urlopen", side_effect=http_error_429),
        pytest.raises(ORSAPIError, match="Rate limit exceeded"),
    ):
        fetch_ors_matrix(mock_monuments, api_key="any-key")
