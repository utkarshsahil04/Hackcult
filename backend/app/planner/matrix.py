"""OpenRouteService distance matrix generator, validator, and persistent storage."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.db.init_db import connect
from app.planner.models import (
    MatrixDimensionError,
    MatrixOrderError,
    ORSAPIError,
    TravelMatrix,
)

logger = logging.getLogger(__name__)

DEFAULT_BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATRIX_DIR = DEFAULT_BACKEND_ROOT / "data" / "matrix"
BUNDLED_MATRIX_DIR = Path(__file__).resolve().parent / "data"

ORS_BASE_URL = "https://api.openrouteservice.org"
SUPPORTED_PROFILES = ("driving-car", "foot-walking")


def read_monuments_from_db(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Read all monuments ordered by id from the SQLite database."""
    conn = connect(db_path, read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT id, slug, name, latitude, longitude, city
            FROM monuments
            ORDER BY id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def default_matrix_path(profile: str) -> Path:
    """Get the default cache path for a profile's travel matrix."""
    return DEFAULT_MATRIX_DIR / f"{profile}_matrix.json"


def bundled_matrix_path(profile: str) -> Path:
    """Get the bundled package path for a profile's travel matrix."""
    return BUNDLED_MATRIX_DIR / f"{profile}_matrix.json"


def save_matrix(matrix: TravelMatrix, path: Path | None = None) -> Path:
    """Save a travel matrix to disk as JSON."""
    target_path = path or default_matrix_path(matrix.profile)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(matrix.to_dict(), indent=2), encoding="utf-8")
    logger.info("Saved %s matrix to %s", matrix.profile, target_path)
    return target_path


def load_matrix(path: Path | str | None = None, profile: str = "driving-car") -> TravelMatrix:
    """Load a travel matrix from cache, falling back to bundled data if needed."""
    if isinstance(path, str):
        if path in SUPPORTED_PROFILES:
            profile = path
            path = None
        else:
            path = Path(path)

    if path is not None and path.is_file():
        target = path
    else:
        default_p = default_matrix_path(profile)
        bundled_p = bundled_matrix_path(profile)
        if default_p.is_file():
            target = default_p
        elif bundled_p.is_file():
            target = bundled_p
        else:
            raise ORSAPIError(
                f"No travel matrix found for profile '{profile}' at '{default_p}' or '{bundled_p}'"
            )

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ORSAPIError(f"Failed to read matrix file at {target}: {exc}") from exc

    return TravelMatrix.from_dict(data)


def validate_matrix_against_monuments(
    matrix: TravelMatrix, monuments: list[dict[str, Any]]
) -> None:
    """Verify that matrix dimensions and coordinate ordering strictly match monuments."""
    n = len(monuments)
    expected_slugs = [m["slug"] for m in monuments]

    if matrix.monument_slugs != expected_slugs:
        raise MatrixOrderError(
            f"Matrix slugs ordering does not match monuments: "
            f"got {matrix.monument_slugs}, expected {expected_slugs}"
        )

    if len(matrix.durations) != n or any(len(r) != n for r in matrix.durations):
        raise MatrixDimensionError(
            f"Matrix durations must be {n}x{n}, got {len(matrix.durations)}"
        )

    for idx, m in enumerate(monuments):
        m_lon, m_lat = float(m["longitude"]), float(m["latitude"])
        loc = matrix.locations[idx]
        # Allow tiny float precision delta (1e-4 deg ~ 10m)
        if abs(loc[0] - m_lon) > 1e-4 or abs(loc[1] - m_lat) > 1e-4:
            raise MatrixOrderError(
                f"Coordinate mismatch at index {idx} ({m['slug']}): "
                f"matrix has {loc}, monument has [{m_lon}, {m_lat}]"
            )


def fetch_ors_matrix(
    monuments: list[dict[str, Any]],
    profile: str = "driving-car",
    api_key: str | None = None,
    base_url: str = ORS_BASE_URL,
    timeout: int = 45,
) -> TravelMatrix:
    """Query the OpenRouteService API for distance and duration matrix.

    Locations are sent in standard GeoJSON format: [[longitude, latitude], ...].
    """
    if profile not in SUPPORTED_PROFILES:
        raise ORSAPIError(
            f"Unsupported profile '{profile}'. Supported: {SUPPORTED_PROFILES}"
        )

    key = api_key or os.environ.get("ORS_API_KEY", "").strip()
    if not key:
        raise ORSAPIError(
            "ORS_API_KEY environment variable is not set. Set ORS_API_KEY or use offline mode."
        )

    slugs = [m["slug"] for m in monuments]
    locations = [[float(m["longitude"]), float(m["latitude"])] for m in monuments]

    url = f"{base_url.rstrip('/')}/v2/matrix/{profile}"
    payload = json.dumps(
        {
            "locations": locations,
            "metrics": ["distance", "duration"],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                raise ORSAPIError(f"ORS API returned HTTP {response.status}")
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        msg = f"ORS API error {exc.code}: {exc.reason}"
        if exc.code == 429:
            msg += " (Rate limit exceeded)"
        elif exc.code in (401, 403):
            msg += " (Authentication failed / Invalid API key)"
        raise ORSAPIError(msg) from exc
    except urllib.error.URLError as exc:
        raise ORSAPIError(f"ORS network error: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ORSAPIError(f"Invalid JSON response from ORS: {exc}") from exc

    durations = data.get("durations")
    distances = data.get("distances")
    if durations is None or distances is None:
        raise ORSAPIError("ORS response missing 'durations' or 'distances'")

    matrix = TravelMatrix(
        profile=profile,
        monument_slugs=slugs,
        locations=locations,
        durations=durations,
        distances=distances,
        created_at=datetime.now(timezone.utc).isoformat(),
        source="openrouteservice",
    )
    matrix.validate()
    validate_matrix_against_monuments(matrix, monuments)
    return matrix


def get_or_fetch_matrix(
    profile: str = "driving-car",
    monuments: list[dict[str, Any]] | None = None,
    db_path: Path | str | None = None,
    offline: bool = False,
    cache_path: Path | None = None,
    api_key: str | None = None,
) -> TravelMatrix:
    """Retrieve travel matrix for profile.

    In offline mode or when ORS_API_KEY is not configured, loads from persistent cache.
    """
    key = api_key or os.environ.get("ORS_API_KEY", "").strip()
    is_offline = (
        offline
        or not key
        or bool(os.environ.get("PLANNER_OFFLINE_MODE", "0") in ("1", "true", "True"))
    )

    if is_offline:
        logger.info("Loading precomputed %s matrix in offline mode", profile)
        matrix = load_matrix(path=cache_path, profile=profile)
        if monuments is not None:
            validate_matrix_against_monuments(matrix, monuments)
        return matrix

    # Online fetch
    mons = monuments or read_monuments_from_db(db_path=db_path)
    logger.info("Fetching live %s matrix from OpenRouteService for %d monuments", profile, len(mons))
    matrix = fetch_ors_matrix(mons, profile=profile, api_key=key)
    save_matrix(matrix, path=cache_path)
    return matrix

