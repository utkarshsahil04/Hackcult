"""Tour itinerary optimizer using Google OR-Tools constraint routing."""

from __future__ import annotations

import logging
import math
from typing import Any

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.planner.models import (
    InfeasibleItineraryError,
    InvalidInputError,
    Itinerary,
    Stop,
    TravelMatrix,
)

logger = logging.getLogger(__name__)

DEFAULT_MONUMENT_VISIT_MINUTES = 60.0
DEFAULT_POI_VISIT_MINUTES = 30.0

DEFAULT_MONUMENT_CITIES: dict[str, str] = {
    "humayuns-tomb": "Delhi",
    "taj-mahal": "Agra",
    "fatehpur-sikri": "Fatehpur Sikri",
    "qutb-complex": "Delhi",
    "red-fort": "Delhi",
    "agra-fort": "Agra",
    "akbars-tomb": "Agra",
    "itimad-ud-daulah": "Agra",
    "jama-masjid": "Delhi",
    "safdarjungs-tomb": "Delhi",
    "purana-qila": "Delhi",
    "tughlaqabad-fort": "Delhi",
    "jantar-mantar": "Delhi",
    "mehrauli-archaeological-park": "Delhi",
    "lodhi-gardens": "Delhi",
}


def _validate_inputs(
    time_budget_minutes: float,
    visit_durations: dict[str, float] | None,
    max_stops: int | None,
    time_limit_seconds: int,
) -> None:
    """Validate numerical constraints and types for itinerary solver inputs."""
    # 1. Budget validation
    if not isinstance(time_budget_minutes, (int, float)) or isinstance(time_budget_minutes, bool):
        raise InvalidInputError(
            f"time_budget_minutes must be a number, got {type(time_budget_minutes).__name__}"
        )
    if math.isnan(time_budget_minutes) or math.isinf(time_budget_minutes):
        raise InvalidInputError(
            f"time_budget_minutes must be a finite number, got {time_budget_minutes}"
        )
    if time_budget_minutes < 0:
        raise InvalidInputError(
            f"time_budget_minutes cannot be negative, got {time_budget_minutes}"
        )

    # 2. Max stops validation
    if max_stops is not None:
        if not isinstance(max_stops, int) or isinstance(max_stops, bool):
            raise InvalidInputError(
                f"max_stops must be an integer, got {type(max_stops).__name__}"
            )
        if max_stops <= 0:
            raise InvalidInputError(
                f"max_stops must be a positive integer (>= 1), got {max_stops}"
            )

    # 3. Solver time limit validation
    if not isinstance(time_limit_seconds, (int, float)) or isinstance(time_limit_seconds, bool):
        raise InvalidInputError(
            f"time_limit_seconds must be a number, got {type(time_limit_seconds).__name__}"
        )
    if math.isnan(time_limit_seconds) or math.isinf(time_limit_seconds) or time_limit_seconds <= 0:
        raise InvalidInputError(
            f"time_limit_seconds must be a positive finite number, got {time_limit_seconds}"
        )

    # 4. Visit durations validation
    if visit_durations is not None:
        if not isinstance(visit_durations, dict):
            raise InvalidInputError(
                f"visit_durations must be a dict, got {type(visit_durations).__name__}"
            )
        for slug, dur in visit_durations.items():
            if not isinstance(dur, (int, float)) or isinstance(dur, bool):
                raise InvalidInputError(
                    f"Visit duration for '{slug}' must be a number, got {type(dur).__name__}"
                )
            if math.isnan(dur) or math.isinf(dur):
                raise InvalidInputError(
                    f"Visit duration for '{slug}' must be a finite number, got {dur}"
                )
            if dur < 0:
                raise InvalidInputError(
                    f"Visit duration for '{slug}' cannot be negative, got {dur}"
                )


def solve_itinerary(
    start_monument: str,
    time_budget_minutes: float,
    matrix: TravelMatrix,
    candidate_slugs: list[str] | None = None,
    visit_durations: dict[str, float] | None = None,
    monument_names: dict[str, str] | None = None,
    return_to_start: bool = False,
    must_visit: list[str] | None = None,
    max_stops: int | None = None,
    preferences: dict[str, Any] | None = None,
    time_limit_seconds: int = 2,
) -> Itinerary:
    """Solve the constrained tour itinerary using Google OR-Tools.

    Parameters
    ----------
    start_monument : str
        Slug of the starting monument.
    time_budget_minutes : float
        Total allowable time (travel + visits) in minutes.
    matrix : TravelMatrix
        Validated travel distance & duration matrix.
    candidate_slugs : list[str], optional
        List of candidate monument slugs to consider. Defaults to matrix slugs.
    visit_durations : dict[str, float], optional
        Mapping of monument slug -> duration in minutes (default: 60m).
    monument_names : dict[str, str], optional
        Mapping of slug -> human-readable monument name.
    return_to_start : bool
        Whether the tour must conclude back at the starting monument.
    must_visit : list[str], optional
        Monuments that must be visited if feasible.
    max_stops : int, optional
        Maximum number of distinct stops allowed (including start).
    preferences : dict, optional
        Optional user preferences:
        - "city": str (preferred city name, e.g. "Delhi" or "Agra").
        - "monument_cities": dict[str, str] (optional custom mapping).
    time_limit_seconds : int
        Maximum OR-Tools solver search time in seconds.

    Returns
    -------
    Itinerary
        Planned tour itinerary with detailed stop timings and feasibility status.
    """
    _validate_inputs(time_budget_minutes, visit_durations, max_stops, time_limit_seconds)

    if start_monument not in matrix.monument_slugs:
        raise InfeasibleItineraryError(
            f"Start monument '{start_monument}' is not found in the travel matrix"
        )

    durations_map = dict(visit_durations or {})
    names_map = dict(monument_names or {})

    # Default duration for starting monument
    start_visit = durations_map.get(start_monument, DEFAULT_MONUMENT_VISIT_MINUTES)

    # Check 1: Budget less than start visit duration
    if time_budget_minutes < start_visit:
        return Itinerary(
            is_feasible=False,
            status_message=(
                f"Time budget of {time_budget_minutes:.1f} minutes is insufficient for the "
                f"starting monument visit duration of {start_visit:.1f} minutes."
            ),
            start_monument=start_monument,
            time_budget_min=time_budget_minutes,
            total_time_min=0.0,
            total_travel_time_min=0.0,
            total_visit_time_min=0.0,
            total_travel_distance_m=0.0,
            stops=[],
            profile=matrix.profile,
            return_to_start=return_to_start,
            solver_status="INFEASIBLE",
        )

    # Validate must_visit destinations
    must_visit_set = set(must_visit or [])
    for mv in must_visit_set:
        if mv not in matrix.monument_slugs:
            raise InfeasibleItineraryError(
                f"Must-visit monument '{mv}' is not present in the travel matrix"
            )

    # Check 2: Max stops enforcement check against mandatory stops
    # Mandatory stops count = start_monument (1) + any other distinct must_visit
    distinct_mandatory = {start_monument} | must_visit_set
    if max_stops is not None and len(distinct_mandatory) > max_stops:
        other_mandatory = must_visit_set - {start_monument}
        return Itinerary(
            is_feasible=False,
            status_message=(
                f"Maximum stops limit ({max_stops}) cannot accommodate the starting monument "
                f"plus {len(other_mandatory)} mandatory destination(s) "
                f"(requires at least {len(distinct_mandatory)} stops)."
            ),
            start_monument=start_monument,
            time_budget_min=time_budget_minutes,
            total_time_min=0.0,
            total_travel_time_min=0.0,
            total_visit_time_min=0.0,
            total_travel_distance_m=0.0,
            stops=[],
            profile=matrix.profile,
            return_to_start=return_to_start,
            solver_status="INFEASIBLE",
        )

    # City preference filtering
    city_map = dict(DEFAULT_MONUMENT_CITIES)
    if preferences and "monument_cities" in preferences and isinstance(preferences["monument_cities"], dict):
        city_map.update(preferences["monument_cities"])

    preferred_city = ""
    if preferences and "city" in preferences and preferences["city"]:
        preferred_city = str(preferences["city"]).strip().lower()

    if candidate_slugs is None:
        raw_candidates = list(matrix.monument_slugs)
    else:
        raw_candidates = list(candidate_slugs)

    # Filter optional candidates by city preference:
    # Always keep start_monument and any must_visit destinations regardless of city preference
    filtered_candidates: list[str] = []
    for s in raw_candidates:
        if s not in matrix.monument_slugs:
            continue
        is_mandatory = (s == start_monument) or (s in must_visit_set)
        matches_city = (not preferred_city) or (city_map.get(s, "").strip().lower() == preferred_city)
        if is_mandatory or matches_city:
            filtered_candidates.append(s)

    # Ensure start_monument is at index 0 without duplicates
    candidates: list[str] = [start_monument]
    for s in filtered_candidates:
        if s != start_monument and s not in candidates:
            candidates.append(s)

    # Ensure all must_visit items are in candidates
    for mv in must_visit_set:
        if mv not in candidates:
            candidates.append(mv)

    n_candidates = len(candidates)
    must_visit_indices = {i for i, s in enumerate(candidates) if s in must_visit_set}

    # If only 1 candidate available
    if n_candidates == 1:
        start_name = names_map.get(start_monument, start_monument.replace("-", " ").title())
        single_stop = Stop(
            monument_slug=start_monument,
            name=start_name,
            arrival_time_min=0.0,
            visit_duration_min=start_visit,
            departure_time_min=start_visit,
            travel_time_to_next_min=0.0,
            travel_distance_to_next_m=0.0,
        )
        return Itinerary(
            is_feasible=True,
            status_message=f"Feasible single-stop tour at {start_name}.",
            start_monument=start_monument,
            time_budget_min=time_budget_minutes,
            total_time_min=start_visit,
            total_travel_time_min=0.0,
            total_visit_time_min=start_visit,
            total_travel_distance_m=0.0,
            stops=[single_stop],
            profile=matrix.profile,
            return_to_start=return_to_start,
            solver_status="SUCCESS",
        )

    # Set up OR-Tools Routing Model
    # For open tour (return_to_start=False), append a dummy end node
    dummy_end_node = n_candidates if not return_to_start else 0
    total_nodes = n_candidates + 1 if not return_to_start else n_candidates

    manager = pywrapcp.RoutingIndexManager(
        total_nodes,
        1,  # 1 vehicle (the traveler)
        [0],  # starts at index 0 (start_monument)
        [dummy_end_node],  # ends at dummy_end_node or 0
    )
    routing = pywrapcp.RoutingModel(manager)

    def transit_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)

        # Transition to dummy end node
        if to_node == dummy_end_node and not return_to_start:
            from_slug = candidates[from_node]
            v_min = durations_map.get(from_slug, DEFAULT_MONUMENT_VISIT_MINUTES)
            return round(v_min * 60)

        # Transition from dummy end node
        if from_node == dummy_end_node and not return_to_start:
            return 0

        from_slug = candidates[from_node]
        to_slug = candidates[to_node]

        if not matrix.has_route(from_slug, to_slug):
            return 100_000_000

        travel_sec = round(matrix.get_travel_time_seconds(from_slug, to_slug))
        visit_sec = round(durations_map.get(from_slug, DEFAULT_MONUMENT_VISIT_MINUTES) * 60)
        return travel_sec + visit_sec

    transit_callback_index = routing.RegisterTransitCallback(transit_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Time dimension constraint
    budget_sec = round(time_budget_minutes * 60)
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        budget_sec,  # maximum capacity is total budget
        True,  # start cumul to zero
        "Time",
    )

    # Stop count dimension constraint (max_stops enforced directly inside OR-Tools)
    if max_stops is not None:
        def stop_count_callback(from_index: int, to_index: int) -> int:
            return 1

        stop_callback_index = routing.RegisterTransitCallback(stop_count_callback)
        routing.AddDimension(
            stop_callback_index,
            0,  # no slack
            max_stops,  # maximum allowed stops
            True,  # start cumul to zero
            "Stops",
        )

    # Optional visits (disjunctions with drop penalty)
    # Only optional nodes have disjunctions. Must-visit nodes have no disjunction (mandatory).
    drop_penalty = 10_000_000
    for node_idx in range(1, n_candidates):
        if node_idx not in must_visit_indices:
            routing.AddDisjunction([manager.NodeToIndex(node_idx)], drop_penalty)

    # Search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = int(time_limit_seconds)

    solution = routing.SolveWithParameters(search_parameters)

    # Honest evaluation of search outcome
    if not solution:
        status_code = routing.status()
        if status_code == routing_enums_pb2.RoutingSearchStatus.ROUTING_FAIL_TIMEOUT:
            solver_status = "TIMEOUT"
            status_msg = (
                f"Solver timed out after {time_limit_seconds}s before proving feasibility "
                f"or finding a route within budget {time_budget_minutes:.1f}m."
            )
        elif status_code == routing_enums_pb2.RoutingSearchStatus.ROUTING_INFEASIBLE:
            solver_status = "INFEASIBLE"
            status_msg = (
                f"Proven infeasible: no route can satisfy time budget ({time_budget_minutes:.1f}m) "
                f"and specified constraints."
            )
        elif status_code == routing_enums_pb2.RoutingSearchStatus.ROUTING_INVALID:
            solver_status = "INVALID"
            status_msg = "Invalid solver model: constraints or parameters were rejected by the solver."
        elif status_code == routing_enums_pb2.RoutingSearchStatus.ROUTING_FAIL:
            solver_status = "NO_SOLUTION_FOUND"
            status_msg = (
                f"Search failed to find a valid route within time budget {time_budget_minutes:.1f}m "
                f"satisfying constraints (status: ROUTING_FAIL)."
            )
        else:
            solver_status = "NOT_SOLVED"
            status_msg = f"No solution found (solver status code {status_code})."

        return Itinerary(
            is_feasible=False,
            status_message=status_msg,
            start_monument=start_monument,
            time_budget_min=time_budget_minutes,
            total_time_min=0.0,
            total_travel_time_min=0.0,
            total_visit_time_min=0.0,
            total_travel_distance_m=0.0,
            stops=[],
            profile=matrix.profile,
            return_to_start=return_to_start,
            solver_status=solver_status,
        )

    # Extract ordered stops from solution
    ordered_indices: list[int] = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        if node < n_candidates:
            ordered_indices.append(node)
        index = solution.Value(routing.NextVar(index))

    # Verify that all must-visit destinations were visited
    visited_slugs = {candidates[c] for c in ordered_indices}
    missing_must_visit = must_visit_set - visited_slugs
    if missing_must_visit:
        return Itinerary(
            is_feasible=False,
            status_message=(
                f"No feasible itinerary found within {time_budget_minutes:.1f}m budget "
                f"satisfying must-visit constraints: {sorted(missing_must_visit)}."
            ),
            start_monument=start_monument,
            time_budget_min=time_budget_minutes,
            total_time_min=0.0,
            total_travel_time_min=0.0,
            total_visit_time_min=0.0,
            total_travel_distance_m=0.0,
            stops=[],
            profile=matrix.profile,
            return_to_start=return_to_start,
            solver_status="INFEASIBLE",
        )

    # For return_to_start, append start if more than 1 stop visited
    if return_to_start and len(ordered_indices) > 1:
        ordered_indices.append(0)

    # Build Stops timeline without truncation
    stops: list[Stop] = []
    current_time_min = 0.0
    total_travel_time_min = 0.0
    total_visit_time_min = 0.0
    total_distance_m = 0.0

    num_stops = len(ordered_indices)
    for idx in range(num_stops):
        c_node = ordered_indices[idx]
        slug = candidates[c_node]
        name = names_map.get(slug, slug.replace("-", " ").title())

        # If return_to_start and this is the return trip back to start (final stop)
        is_final_return = return_to_start and idx == num_stops - 1 and idx > 0
        v_min = 0.0 if is_final_return else durations_map.get(slug, DEFAULT_MONUMENT_VISIT_MINUTES)

        arr_min = round(current_time_min, 2)
        dep_min = round(arr_min + v_min, 2)
        total_visit_time_min += v_min

        trav_to_next_min = 0.0
        dist_to_next_m = 0.0

        if idx < num_stops - 1:
            next_node = ordered_indices[idx + 1]
            next_slug = candidates[next_node]
            trav_to_next_min = round(matrix.get_travel_time_minutes(slug, next_slug), 2)
            dist_to_next_m = round(matrix.get_travel_distance_meters(slug, next_slug), 1)
            total_travel_time_min += trav_to_next_min
            total_distance_m += dist_to_next_m
            current_time_min = dep_min + trav_to_next_min
        else:
            current_time_min = dep_min

        stops.append(
            Stop(
                monument_slug=slug,
                name=name,
                arrival_time_min=arr_min,
                visit_duration_min=v_min,
                departure_time_min=dep_min,
                travel_time_to_next_min=trav_to_next_min,
                travel_distance_to_next_m=dist_to_next_m,
            )
        )

    calc_total_time = round(total_visit_time_min + total_travel_time_min, 2)

    msg = (
        f"Generated {len(stops)}-stop itinerary visiting "
        f"{', '.join(s.monument_slug for s in stops)} "
        f"in {calc_total_time:.1f}m (budget {time_budget_minutes:.1f}m)."
    )

    return Itinerary(
        is_feasible=True,
        status_message=msg,
        start_monument=start_monument,
        time_budget_min=time_budget_minutes,
        total_time_min=calc_total_time,
        total_travel_time_min=round(total_travel_time_min, 2),
        total_visit_time_min=round(total_visit_time_min, 2),
        total_travel_distance_m=round(total_distance_m, 1),
        stops=stops,
        profile=matrix.profile,
        return_to_start=return_to_start,
        solver_status="SUCCESS",
    )
