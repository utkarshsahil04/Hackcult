from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class SourceOut(BaseModel):
    title: str
    url: str
    publisher: str
    source_type: str
    note: str | None = None  # paraphrase of what this source says about the claim


class ClaimOut(BaseModel):
    key: str
    type: str
    text: str
    is_legend: bool
    sources: list[SourceOut]


class MonumentSummary(BaseModel):
    slug: str
    name: str
    city: str


class MonumentProfile(BaseModel):
    slug: str
    name: str
    description: str
    latitude: float
    longitude: float
    era: str
    architectural_style: str
    location: str
    city: str
    claims: list[ClaimOut]
    sources: list[SourceOut]  # every source behind this monument, deduplicated


class RelatedItem(BaseModel):
    relation_type: str
    direction: Literal["outgoing", "incoming"]
    note: str
    monument: MonumentSummary
    sources: list[SourceOut]  # evidence behind the edge's claim


class RelatedResponse(BaseModel):
    monument: MonumentSummary
    related: list[RelatedItem]


# --- Nearby Places Schemas (Issue #10) ---


class PlaceOut(BaseModel):
    name: str
    category: str
    latitude: float
    longitude: float
    osm_id: int
    osm_type: str = "node"
    source: str = "overpass"
    associated_monument: str = ""
    distance_m: float | None = None
    tags: dict[str, str] = Field(default_factory=dict)


# --- Tour Planning Schemas (Issue #10) ---


class RouteLineRequest(BaseModel):
    stops: list[str] = Field(description="Monument slugs in visiting order")
    profile: Literal["driving-car", "foot-walking"] = "driving-car"


class RouteLineResponse(BaseModel):
    source: Literal["roads", "straight"]
    legs: list[list[list[float]]] = Field(description="One [latitude, longitude] line per leg")


class TourPlanRequest(BaseModel):
    query: str | None = Field(
        default=None,
        max_length=500,
        description="Natural language trip description or visitor preferences (e.g. '3 hour tour in Delhi starting at Red Fort')",
    )
    start_monument: str | None = Field(
        default=None,
        description="Slug of the starting monument (e.g. 'red-fort')",
    )
    time_budget_minutes: float | None = Field(
        default=None,
        gt=0,
        description="Total tour time budget in minutes",
    )
    must_visit: list[str] = Field(
        default_factory=list,
        description="List of monument slugs that must be visited",
    )
    preferences: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional filter preferences such as {'city': 'Delhi'}",
    )
    profile: Literal["driving-car", "foot-walking"] = "driving-car"
    return_to_start: bool = False
    max_stops: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of monuments to visit",
    )
    visit_durations: dict[str, float] = Field(
        default_factory=dict,
        description="Custom visit duration in minutes per monument slug",
    )
    preset: str | None = Field(
        default=None, description="Plan preset from planner/data/plan_presets.json (relaxed, standard, quick)"
    )
    max_leg_min: float | None = Field(default=None, gt=0, description="Longest allowed travel leg in minutes")
    interests: list[str] = Field(
        default_factory=list, description="Interest keywords (e.g. 'mughal', 'garden') that raise a site's priority"
    )
    time_limit_seconds: int = Field(
        default=5,
        ge=1,
        le=10,
        description="OR-Tools solver computation time limit in seconds",
    )

    @model_validator(mode="after")
    def check_query_or_start(self) -> TourPlanRequest:
        has_query = bool(self.query and self.query.strip())
        has_direct = bool(self.start_monument and self.start_monument.strip())
        if not has_query and not has_direct and not self.time_budget_minutes:
            raise ValueError(
                "Provide 'query', 'start_monument' or 'time_budget_minutes' (the start is then chosen for you)."
            )
        return self


class StopOut(BaseModel):
    monument_slug: str
    name: str
    arrival_time_min: float
    visit_duration_min: float
    departure_time_min: float
    travel_time_to_next_min: float = 0.0
    travel_distance_to_next_m: float = 0.0


class ItineraryOut(BaseModel):
    is_feasible: bool
    status_message: str
    start_monument: str
    time_budget_min: float
    total_time_min: float
    total_travel_time_min: float
    total_visit_time_min: float
    total_travel_distance_m: float
    stops: list[StopOut] = Field(default_factory=list)
    profile: str = "driving-car"
    return_to_start: bool = False
    solver_status: str = "SUCCESS"


class ValidationOut(BaseModel):
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recalculated_total_time_min: float = 0.0
    recalculated_travel_time_min: float = 0.0
    recalculated_visit_time_min: float = 0.0
    recalculated_distance_m: float = 0.0


class PlanMetricsOut(BaseModel):
    stop_count: int
    max_stops: int
    budget_utilisation: float  # planned minutes / budget
    travel_share: float  # travel minutes / planned minutes
    slack_min: float  # unused budget
    is_optimal: bool | None = None  # matches the exhaustive-search optimum (None when not checked)
    preset: str


class TourPlanResponse(BaseModel):
    is_feasible: bool
    status_message: str
    solver_status: str
    is_validated: bool
    itinerary: ItineraryOut | None = None
    validation: ValidationOut | None = None
    explanation: str | None = None
    parsed_preferences: dict[str, Any] | None = None
    metrics: PlanMetricsOut | None = None
