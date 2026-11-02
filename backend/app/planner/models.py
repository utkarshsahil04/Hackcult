"""Domain models and exceptions for the Raahein Tour Planner."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PlannerError(Exception):
    """Base class for all planner errors."""


class OverpassError(PlannerError):
    """Base class for Overpass API and POI caching errors."""


class CacheError(OverpassError):
    """Raised when reading or writing cache fails."""


class CacheNotFoundError(CacheError):
    """Raised when an expected cache file does not exist (e.g. offline mode)."""


class CacheExpiredError(CacheError):
    """Raised when cache has expired and fresh data is required."""


class MatrixError(PlannerError):
    """Base class for distance/duration travel matrix errors."""


class MatrixDimensionError(MatrixError):
    """Raised when matrix dimensions do not match the expected NxN size."""


class MatrixOrderError(MatrixError):
    """Raised when matrix coordinate ordering does not match monuments."""


class MissingRouteError(MatrixError):
    """Raised when no route exists between two locations in the matrix."""


class ORSAPIError(MatrixError):
    """Raised when an OpenRouteService API request fails or returns an error."""


class SolverError(PlannerError):
    """Base class for OR-Tools tour solving errors."""


class InvalidInputError(SolverError, ValueError):
    """Raised when planner input parameters are invalid (e.g. NaN, infinite, negative, or wrong type)."""


class InfeasibleItineraryError(SolverError):
    """Raised when no feasible tour exists within the requested budget or constraints."""


class RouteValidationError(PlannerError):
    """Raised when independent route validation fails."""


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class POI:
    """A Point of Interest located near a heritage monument."""

    name: str
    category: str
    latitude: float
    longitude: float
    osm_id: int
    osm_type: str
    source: str = "overpass"
    associated_monument: str = ""
    distance_m: float | None = None
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> POI:
        """Instantiate a POI from a dictionary."""
        return cls(
            name=str(data.get("name", "")).strip(),
            category=str(data.get("category", "other")).strip().lower(),
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            osm_id=int(data["osm_id"]),
            osm_type=str(data.get("osm_type", "node")),
            source=str(data.get("source", "overpass")),
            associated_monument=str(data.get("associated_monument", "")),
            distance_m=float(data["distance_m"]) if data.get("distance_m") is not None else None,
            tags=dict(data.get("tags", {})),
        )


@dataclass
class TravelMatrix:
    """NxN travel distance and duration matrix for a specific transport profile."""

    profile: str
    monument_slugs: list[str]
    locations: list[list[float]]  # [[lon, lat], ...]
    durations: list[list[float | None]]  # seconds (None if no route exists)
    distances: list[list[float | None]]  # meters (None if no route exists)
    created_at: str
    source: str = "openrouteservice"

    def __post_init__(self) -> None:
        self._slug_to_index: dict[str, int] = {
            slug: idx for idx, slug in enumerate(self.monument_slugs)
        }

    def validate(self) -> None:
        """Validate matrix structure, square dimensions, and non-negativity."""
        n = len(self.monument_slugs)
        if len(self.locations) != n:
            raise MatrixDimensionError(
                f"Locations length ({len(self.locations)}) does not match slugs ({n})"
            )
        if len(self.durations) != n or any(len(row) != n for row in self.durations):
            raise MatrixDimensionError(
                f"Durations matrix must be {n}x{n}, got {len(self.durations)} rows"
            )
        if len(self.distances) != n or any(len(row) != n for row in self.distances):
            raise MatrixDimensionError(
                f"Distances matrix must be {n}x{n}, got {len(self.distances)} rows"
            )

        for i in range(n):
            for j in range(n):
                dur, dist = self.durations[i][j], self.distances[i][j]
                if i == j:
                    if dur != 0.0 or dist != 0.0:
                        raise MatrixError(
                            f"Diagonal entry ({self.monument_slugs[i]}) must be 0, got dur={dur}, dist={dist}"
                        )
                else:
                    if dur is not None and dur < 0:
                        raise MatrixError(f"Negative duration at [{i}][{j}]: {dur}")
                    if dist is not None and dist < 0:
                        raise MatrixError(f"Negative distance at [{i}][{j}]: {dist}")

    def has_route(self, from_slug: str, to_slug: str) -> bool:
        """Check if a route exists between two monuments."""
        if from_slug not in self._slug_to_index or to_slug not in self._slug_to_index:
            return False
        i = self._slug_to_index[from_slug]
        j = self._slug_to_index[to_slug]
        return self.durations[i][j] is not None and self.distances[i][j] is not None

    def get_travel_time_seconds(self, from_slug: str, to_slug: str) -> float:
        """Get travel duration in seconds between two monuments."""
        if from_slug == to_slug:
            return 0.0
        if from_slug not in self._slug_to_index:
            raise MissingRouteError(f"Monument '{from_slug}' is not in the travel matrix")
        if to_slug not in self._slug_to_index:
            raise MissingRouteError(f"Monument '{to_slug}' is not in the travel matrix")
        i = self._slug_to_index[from_slug]
        j = self._slug_to_index[to_slug]
        val = self.durations[i][j]
        if val is None:
            raise MissingRouteError(
                f"No travel route exists from '{from_slug}' to '{to_slug}' for profile '{self.profile}'"
            )
        return float(val)

    def get_travel_time_minutes(self, from_slug: str, to_slug: str) -> float:
        """Get travel duration in minutes between two monuments."""
        return self.get_travel_time_seconds(from_slug, to_slug) / 60.0

    def get_travel_distance_meters(self, from_slug: str, to_slug: str) -> float:
        """Get travel distance in meters between two monuments."""
        if from_slug == to_slug:
            return 0.0
        if from_slug not in self._slug_to_index:
            raise MissingRouteError(f"Monument '{from_slug}' is not in the travel matrix")
        if to_slug not in self._slug_to_index:
            raise MissingRouteError(f"Monument '{to_slug}' is not in the travel matrix")
        i = self._slug_to_index[from_slug]
        j = self._slug_to_index[to_slug]
        val = self.distances[i][j]
        if val is None:
            raise MissingRouteError(
                f"No travel route exists from '{from_slug}' to '{to_slug}' for profile '{self.profile}'"
            )
        return float(val)

    def to_dict(self) -> dict[str, Any]:
        """Convert matrix to a JSON-serializable dictionary."""
        return {
            "profile": self.profile,
            "monument_slugs": self.monument_slugs,
            "locations": self.locations,
            "durations": self.durations,
            "distances": self.distances,
            "created_at": self.created_at,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TravelMatrix:
        """Create a TravelMatrix from dictionary."""
        matrix = cls(
            profile=str(data.get("profile", "driving-car")),
            monument_slugs=list(data["monument_slugs"]),
            locations=list(data["locations"]),
            durations=list(data["durations"]),
            distances=list(data["distances"]),
            created_at=str(data.get("created_at", "")),
            source=str(data.get("source", "openrouteservice")),
        )
        matrix.validate()
        return matrix


@dataclass(frozen=True)
class Stop:
    """A scheduled stop in an itinerary."""

    monument_slug: str
    name: str
    arrival_time_min: float
    visit_duration_min: float
    departure_time_min: float
    travel_time_to_next_min: float = 0.0
    travel_distance_to_next_m: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Itinerary:
    """A complete planned tour itinerary generated by the solver."""

    is_feasible: bool
    status_message: str
    start_monument: str
    time_budget_min: float
    total_time_min: float
    total_travel_time_min: float
    total_visit_time_min: float
    total_travel_distance_m: float
    stops: list[Stop] = field(default_factory=list)
    profile: str = "driving-car"
    return_to_start: bool = False
    solver_status: str = "SUCCESS"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stops"] = [s.to_dict() for s in self.stops]
        return data


@dataclass
class ValidationResult:
    """Result of an independent itinerary verification check."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recalculated_total_time_min: float = 0.0
    recalculated_travel_time_min: float = 0.0
    recalculated_visit_time_min: float = 0.0
    recalculated_distance_m: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
