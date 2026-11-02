from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.errors import AppError
from app.planner.matrix import load_matrix
from app.planner.models import (
    InvalidInputError,
    Itinerary,
    MatrixError,
    PlannerError,
    SolverError,
)
from app.planner.solver import solve_itinerary
from app.planner.validator import validate_itinerary
from app.schemas import (
    ItineraryOut,
    StopOut,
    TourPlanRequest,
    TourPlanResponse,
    ValidationOut,
)
from app.services.gemini import (
    VALID_SLUGS,
    GeminiService,
    ParsedConstraints,
    get_gemini_service,
)

logger = logging.getLogger("raahein.api.tours")

router = APIRouter(prefix="/api/tours", tags=["tours"])


def _to_itinerary_out(itinerary: Itinerary) -> ItineraryOut:
    return ItineraryOut(
        is_feasible=itinerary.is_feasible,
        status_message=itinerary.status_message,
        start_monument=itinerary.start_monument,
        time_budget_min=itinerary.time_budget_min,
        total_time_min=itinerary.total_time_min,
        total_travel_time_min=itinerary.total_travel_time_min,
        total_visit_time_min=itinerary.total_visit_time_min,
        total_travel_distance_m=itinerary.total_travel_distance_m,
        stops=[
            StopOut(
                monument_slug=s.monument_slug,
                name=s.name,
                arrival_time_min=s.arrival_time_min,
                visit_duration_min=s.visit_duration_min,
                departure_time_min=s.departure_time_min,
                travel_time_to_next_min=s.travel_time_to_next_min,
                travel_distance_to_next_m=s.travel_distance_to_next_m,
            )
            for s in itinerary.stops
        ],
        profile=itinerary.profile,
        return_to_start=itinerary.return_to_start,
        solver_status=itinerary.solver_status,
    )


@router.post("/plan", response_model=TourPlanResponse)
def plan_tour(
    payload: TourPlanRequest,
    gemini: Annotated[GeminiService, Depends(get_gemini_service)],
) -> TourPlanResponse:
    """Plan an optimal, constraint-checked heritage tour using OR-Tools and Gemini.

    Workflow:
    1. Parse natural-language preferences with Gemini (if query provided).
    2. Merge structured constraints with explicit request overrides.
    3. Run OR-Tools solver to compute the exact itinerary.
    4. Run independent RouteValidator to mathematically verify the route.
    5. Explain the verified itinerary with Gemini (without altering route or stops).
    """
    parsed = ParsedConstraints()
    if payload.query and payload.query.strip():
        parsed = gemini.parse_preferences(payload.query)

    # Merge explicit parameters with parsed preferences (explicit takes precedence)
    start_monument = payload.start_monument or parsed.start_monument
    time_budget_minutes = payload.time_budget_minutes or parsed.time_budget_minutes

    # Combine must_visit lists
    combined_must_visit = list(payload.must_visit)
    for slug in parsed.must_visit:
        if slug not in combined_must_visit and slug != start_monument:
            combined_must_visit.append(slug)

    # Merge preferences dict
    preferences: dict[str, Any] = {**parsed.preferences, **payload.preferences}

    # Profile & return_to_start
    profile = payload.profile
    return_to_start = payload.return_to_start or parsed.return_to_start
    max_stops = payload.max_stops or parsed.max_stops
    visit_durations = {**parsed.visit_durations, **payload.visit_durations}
    time_limit_seconds = payload.time_limit_seconds

    # Validate essential fields
    if not start_monument:
        raise AppError(
            status_code=400,
            code="VALIDATION_ERROR",
            message="Starting monument could not be determined. Please specify 'start_monument' or mention a valid monument in your query.",
            hint="Use a valid monument slug such as 'humayuns-tomb' or 'taj-mahal'.",
        )

    if start_monument not in VALID_SLUGS:
        raise AppError(
            status_code=400,
            code="VALIDATION_ERROR",
            message=f"Unknown starting monument '{start_monument}'.",
            hint=f"Valid slugs are: {', '.join(VALID_SLUGS)}",
        )

    if time_budget_minutes is None or time_budget_minutes <= 0:
        raise AppError(
            status_code=400,
            code="VALIDATION_ERROR",
            message="Time budget could not be determined. Please specify 'time_budget_minutes' or mention tour duration in your query (e.g. '3 hours').",
            hint="Provide a positive number of minutes, e.g. 180.",
        )

    # Load precomputed travel matrix
    try:
        matrix = load_matrix(profile=profile)
    except MatrixError as exc:
        logger.error("Failed to load travel matrix for profile '%s': %s", profile, exc)
        raise AppError(
            status_code=502,
            code="UPSTREAM_MATRIX_UNAVAILABLE",
            message=f"Travel matrix for transport profile '{profile}' is unavailable.",
            hint="Ensure precomputed matrices are available.",
        ) from exc

    # 3. Solve itinerary using OR-Tools
    try:
        itinerary = solve_itinerary(
            start_monument=start_monument,
            time_budget_minutes=time_budget_minutes,
            matrix=matrix,
            must_visit=combined_must_visit,
            preferences=preferences,
            return_to_start=return_to_start,
            max_stops=max_stops,
            visit_durations=visit_durations,
            time_limit_seconds=time_limit_seconds,
        )
    except InvalidInputError as exc:
        raise AppError(
            status_code=400,
            code="VALIDATION_ERROR",
            message=str(exc),
            hint="Check solver input parameters (monument slugs, budget, stops).",
        ) from exc
    except (SolverError, PlannerError) as exc:
        logger.error("Solver execution error: %s", exc)
        raise AppError(
            status_code=500,
            code="SOLVER_ERROR",
            message=f"Failed to solve tour itinerary: {exc}",
            hint="Please retry with different constraints.",
        ) from exc

    parsed_dict = {
        "start_monument": start_monument,
        "time_budget_minutes": time_budget_minutes,
        "must_visit": combined_must_visit,
        "preferences": preferences,
        "profile": profile,
        "return_to_start": return_to_start,
        "max_stops": max_stops,
    }

    # 4. Handle infeasible solver outcome
    if not itinerary.is_feasible:
        explanation = gemini.explain_itinerary(itinerary)
        return TourPlanResponse(
            is_feasible=False,
            status_message=itinerary.status_message,
            solver_status=itinerary.solver_status,
            is_validated=False,
            itinerary=_to_itinerary_out(itinerary),
            validation=None,
            explanation=explanation,
            parsed_preferences=parsed_dict,
        )

    # 5. Independent validation
    validation = validate_itinerary(
        itinerary,
        matrix=matrix,
        time_budget_minutes=time_budget_minutes,
        visit_durations=visit_durations,
    )

    # 6. Verify validation outcome
    if not validation.is_valid:
        error_summary = "; ".join(validation.errors)
        return TourPlanResponse(
            is_feasible=True,
            status_message=f"Itinerary generated but failed verification: {error_summary}",
            solver_status=itinerary.solver_status,
            is_validated=False,
            itinerary=_to_itinerary_out(itinerary),
            validation=ValidationOut(
                is_valid=False,
                errors=validation.errors,
                warnings=validation.warnings,
                recalculated_total_time_min=validation.recalculated_total_time_min,
                recalculated_travel_time_min=validation.recalculated_travel_time_min,
                recalculated_visit_time_min=validation.recalculated_visit_time_min,
                recalculated_distance_m=validation.recalculated_distance_m,
            ),
            explanation=(
                f"Warning: Although a route was calculated, it failed independent mathematical verification: "
                f"{error_summary}. This itinerary cannot be certified as valid."
            ),
            parsed_preferences=parsed_dict,
        )

    # 7. Generate natural language explanation for already-validated itinerary
    explanation = gemini.explain_itinerary(itinerary)

    return TourPlanResponse(
        is_feasible=True,
        status_message=itinerary.status_message,
        solver_status=itinerary.solver_status,
        is_validated=True,
        itinerary=_to_itinerary_out(itinerary),
        validation=ValidationOut(
            is_valid=True,
            errors=validation.errors,
            warnings=validation.warnings,
            recalculated_total_time_min=validation.recalculated_total_time_min,
            recalculated_travel_time_min=validation.recalculated_travel_time_min,
            recalculated_visit_time_min=validation.recalculated_visit_time_min,
            recalculated_distance_m=validation.recalculated_distance_m,
        ),
        explanation=explanation,
        parsed_preferences=parsed_dict,
    )
