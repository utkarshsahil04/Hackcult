from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends

import sqlite3

from app.db import get_db
from app.errors import AppError
from app.planner.config import interest_priorities, resolve_config, restrict_legs
from app.planner.exhaustive import best_plan
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
    PlanMetricsOut,
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


def _metrics(itinerary: Itinerary, cfg, optimum, priorities: dict[str, int]) -> PlanMetricsOut:
    planned = itinerary.total_time_min or 0.0
    budget = itinerary.time_budget_min
    score = sum(1 + priorities.get(s.monument_slug, 0) for s in itinerary.stops)
    # optimal = same weighted visits as the exact search and no more than a minute slower
    optimal = None if optimum is None else (score, -planned) >= (optimum[0][0], optimum[0][1] - 1.0)
    return PlanMetricsOut(
        stop_count=len(itinerary.stops),
        max_stops=cfg.max_stops,
        budget_utilisation=round(planned / budget, 3) if budget else 0.0,
        travel_share=round(itinerary.total_travel_time_min / planned, 3) if planned else 0.0,
        slack_min=round(budget - planned, 2),
        is_optimal=optimal,
        preset=cfg.preset,
    )


@router.post("/plan", response_model=TourPlanResponse)
def plan_tour(
    payload: TourPlanRequest,
    gemini: Annotated[GeminiService, Depends(get_gemini_service)],
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
) -> TourPlanResponse:
    """Plan an optimal, constraint-checked heritage tour using OR-Tools and Gemini.

    Workflow:
    1. Parse natural-language preferences with Gemini (if query provided).
    2. Merge structured constraints with explicit request overrides.
    3. Run OR-Tools solver to compute the exact itinerary.
    4. Run independent RouteValidator to mathematically verify the route.
    5. Explain the verified itinerary with Gemini (without altering route or stops).
    """
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT slug, name, city, era, architectural_style, "
            "NOT EXISTS (SELECT 1 FROM claims c WHERE c.monument_id = m.id) AS listed, "
            "EXISTS (SELECT 1 FROM claims c WHERE c.monument_id = m.id AND c.is_legend = 1) AS has_legend "
            "FROM monuments m ORDER BY id"
        )
    ]
    VALID_SLUGS[:] = [r["slug"] for r in rows]  # the DB, not a hard-coded list, defines what exists
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
    try:
        cfg = resolve_config(payload.preset, payload.max_stops or parsed.max_stops, payload.max_leg_min)
    except InvalidInputError as exc:
        raise AppError(status_code=400, code="VALIDATION_ERROR", message=str(exc), hint="Use relaxed, standard or quick.") from exc
    listed = {r["slug"] for r in rows if r["listed"]}
    visit_durations = {
        **{r["slug"]: cfg.visit_minutes(r["slug"], r["slug"] in listed) for r in rows},
        **parsed.visit_durations,
        **payload.visit_durations,
    }
    priorities = interest_priorities(rows, payload.interests)
    preferences["monument_cities"] = {r["slug"]: r["city"] for r in rows}
    time_limit_seconds = payload.time_limit_seconds

    if start_monument and start_monument not in VALID_SLUGS:
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

    matrix = restrict_legs(matrix, cfg.max_leg_min)
    city = str(preferences.get("city") or "").strip().lower()
    pool = [r["slug"] for r in rows if not city or r["city"].lower() == city]
    must = set(combined_must_visit)

    def optimum(start: str | None):
        return best_plan(matrix, time_budget_minutes, cfg.max_stops, visit_durations, pool,
                         start=start, must_visit=must, priorities=priorities)

    if not start_monument:  # let the exact search pick the best place to begin
        found = optimum(None)
        start_monument = found[1][0] if found else pool[0]
        combined_must_visit = [s for s in combined_must_visit if s != start_monument]

    # 3. Solve itinerary using OR-Tools
    try:
        itinerary = solve_itinerary(
            start_monument=start_monument,
            time_budget_minutes=time_budget_minutes,
            matrix=matrix,
            must_visit=combined_must_visit,
            preferences=preferences,
            return_to_start=return_to_start,
            max_stops=cfg.max_stops,
            visit_durations=visit_durations,
            time_limit_seconds=time_limit_seconds,
            priorities=priorities,
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
        "max_stops": cfg.max_stops,
        "preset": cfg.preset,
        "max_leg_min": cfg.max_leg_min,
        "interests": payload.interests,
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

    metrics = _metrics(itinerary, cfg, optimum(start_monument) if not return_to_start else None, priorities)

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
        metrics=metrics,
    )
