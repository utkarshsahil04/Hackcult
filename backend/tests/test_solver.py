"""Tests for the OR-Tools tour solver: max_stops, city preference, input validation, search outcomes, and constraints."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from ortools.constraint_solver import routing_enums_pb2

from app.planner.matrix import load_matrix
from app.planner.models import (
    InfeasibleItineraryError,
    InvalidInputError,
    TravelMatrix,
)
from app.planner.solver import solve_itinerary


@pytest.fixture
def bundled_matrix() -> TravelMatrix:
    """Load the precomputed bundled 15-monument driving matrix."""
    return load_matrix(profile="driving-car")


# ---------------------------------------------------------------------------
# Basic & Route Constraint Tests
# ---------------------------------------------------------------------------


def test_normal_itinerary_generation(bundled_matrix: TravelMatrix):
    """Test generating a normal 4-hour (240 min) tour starting from Humayun's Tomb."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=240.0,
        matrix=bundled_matrix,
        return_to_start=False,
    )

    assert itinerary.is_feasible is True
    assert itinerary.start_monument == "humayuns-tomb"
    assert len(itinerary.stops) >= 2
    assert itinerary.stops[0].monument_slug == "humayuns-tomb"
    assert itinerary.total_time_min <= 240.0
    assert itinerary.total_travel_time_min > 0.0
    assert itinerary.total_visit_time_min > 0.0
    assert itinerary.solver_status == "SUCCESS"
    assert "Generated" in itinerary.status_message


def test_tight_time_budget(bundled_matrix: TravelMatrix):
    """With tight budget (e.g. 70m for 60m visit), only feasible single stop is generated."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=70.0,
        matrix=bundled_matrix,
        visit_durations={"humayuns-tomb": 60.0},
    )

    assert itinerary.is_feasible is True
    assert len(itinerary.stops) == 1
    assert itinerary.stops[0].monument_slug == "humayuns-tomb"
    assert itinerary.total_time_min == 60.0


def test_impossible_time_budget_less_than_start_visit(bundled_matrix: TravelMatrix):
    """When budget is less than start monument's visit duration, returns is_feasible=False with explanation."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=30.0,
        matrix=bundled_matrix,
        visit_durations={"humayuns-tomb": 60.0},
    )

    assert itinerary.is_feasible is False
    assert len(itinerary.stops) == 0
    assert itinerary.solver_status == "INFEASIBLE"
    assert "insufficient" in itinerary.status_message


def test_must_visit_constraint(bundled_matrix: TravelMatrix):
    """Verify that must-visit monument is prioritized in the tour."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=360.0,
        matrix=bundled_matrix,
        must_visit=["safdarjungs-tomb"],
    )

    assert itinerary.is_feasible is True
    visited = [s.monument_slug for s in itinerary.stops]
    assert "safdarjungs-tomb" in visited


def test_impossible_must_visit_returns_infeasible(bundled_matrix: TravelMatrix):
    """When a must-visit destination is geographically unreachable in budget, returns is_feasible=False."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=120.0,
        matrix=bundled_matrix,
        candidate_slugs=["humayuns-tomb", "taj-mahal"],
        must_visit=["taj-mahal"],
    )

    assert itinerary.is_feasible is False
    assert itinerary.solver_status == "INFEASIBLE"
    assert "infeasible" in itinerary.status_message.lower()


def test_unknown_start_monument_raises(bundled_matrix: TravelMatrix):
    """Starting from an unknown monument raises InfeasibleItineraryError."""
    with pytest.raises(InfeasibleItineraryError, match="not found in the travel matrix"):
        solve_itinerary(
            start_monument="atlantis-temple",
            time_budget_minutes=120.0,
            matrix=bundled_matrix,
        )


# ---------------------------------------------------------------------------
# Max Stops Enforcement Tests
# ---------------------------------------------------------------------------


def test_max_stops_one_with_mandatory_destination_is_infeasible(bundled_matrix: TravelMatrix):
    """max_stops=1 with 1 mandatory destination other than start requires 2 stops -> infeasible."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=300.0,
        matrix=bundled_matrix,
        must_visit=["safdarjungs-tomb"],
        max_stops=1,
    )

    assert itinerary.is_feasible is False
    assert itinerary.solver_status == "INFEASIBLE"
    assert "cannot accommodate the starting monument plus 1 mandatory destination" in itinerary.status_message


def test_max_stops_two_with_one_mandatory_destination(bundled_matrix: TravelMatrix):
    """max_stops=2 with 1 mandatory destination visits exactly start + mandatory stop."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=360.0,
        matrix=bundled_matrix,
        must_visit=["safdarjungs-tomb"],
        max_stops=2,
    )

    assert itinerary.is_feasible is True
    visited = [s.monument_slug for s in itinerary.stops]
    assert len(visited) == 2
    assert visited[0] == "humayuns-tomb"
    assert visited[1] == "safdarjungs-tomb"


def test_max_stops_round_trip(bundled_matrix: TravelMatrix):
    """For round trips, max_stops=2 visits start + 1 other stop + returns to start (2 distinct stops)."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=360.0,
        matrix=bundled_matrix,
        return_to_start=True,
        max_stops=2,
    )

    assert itinerary.is_feasible is True
    assert itinerary.return_to_start is True
    assert len(itinerary.stops) == 3  # [start, stop1, start]
    assert itinerary.stops[0].monument_slug == "humayuns-tomb"
    assert itinerary.stops[-1].monument_slug == "humayuns-tomb"

    distinct_slugs = {s.monument_slug for s in itinerary.stops}
    assert len(distinct_slugs) == 2


def test_max_stops_normal_route(bundled_matrix: TravelMatrix):
    """A normal route with max_stops=3 never visits more than 3 distinct monuments."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=600.0,
        matrix=bundled_matrix,
        max_stops=3,
    )

    assert itinerary.is_feasible is True
    assert len(itinerary.stops) <= 3


def test_max_stops_invalid_values_raise(bundled_matrix: TravelMatrix):
    """Zero, negative, or non-integer max_stops raise InvalidInputError."""
    with pytest.raises(InvalidInputError, match="must be a positive integer"):
        solve_itinerary("humayuns-tomb", 120.0, bundled_matrix, max_stops=0)

    with pytest.raises(InvalidInputError, match="must be a positive integer"):
        solve_itinerary("humayuns-tomb", 120.0, bundled_matrix, max_stops=-2)

    with pytest.raises(InvalidInputError, match="must be an integer"):
        solve_itinerary("humayuns-tomb", 120.0, bundled_matrix, max_stops=2.5)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# City Preference Filtering Tests
# ---------------------------------------------------------------------------


def test_city_preference_matching_city(bundled_matrix: TravelMatrix):
    """Tour starting in Delhi with Delhi city preference only visits Delhi monuments."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=480.0,
        matrix=bundled_matrix,
        preferences={"city": "Delhi"},
    )

    assert itinerary.is_feasible is True
    delhi_monuments = {
        "humayuns-tomb", "qutb-complex", "red-fort", "jama-masjid",
        "safdarjungs-tomb", "purana-qila", "tughlaqabad-fort",
        "jantar-mantar", "mehrauli-archaeological-park", "lodhi-gardens",
    }
    for stop in itinerary.stops:
        assert stop.monument_slug in delhi_monuments


def test_city_preference_non_matching_start_city(bundled_matrix: TravelMatrix):
    """Starting monument outside preferred city is NOT silently removed."""
    itinerary = solve_itinerary(
        start_monument="taj-mahal",  # In Agra
        time_budget_minutes=120.0,
        matrix=bundled_matrix,
        preferences={"city": "Delhi"},
    )

    assert itinerary.is_feasible is True
    assert itinerary.stops[0].monument_slug == "taj-mahal"


def test_city_preference_mandatory_destination_outside_preferred_city(bundled_matrix: TravelMatrix):
    """Mandatory destinations outside preferred city are preserved and visited."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=600.0,
        matrix=bundled_matrix,
        must_visit=["taj-mahal"],  # In Agra
        preferences={"city": "Delhi"},
    )

    assert itinerary.is_feasible is True
    visited = [s.monument_slug for s in itinerary.stops]
    assert "humayuns-tomb" in visited
    assert "taj-mahal" in visited


# ---------------------------------------------------------------------------
# Input Validation Tests
# ---------------------------------------------------------------------------


def test_input_validation_time_budget(bundled_matrix: TravelMatrix):
    """Negative, NaN, or infinite time budgets raise InvalidInputError."""
    with pytest.raises(InvalidInputError, match="cannot be negative"):
        solve_itinerary("humayuns-tomb", -10.0, bundled_matrix)

    with pytest.raises(InvalidInputError, match="finite number"):
        solve_itinerary("humayuns-tomb", float("nan"), bundled_matrix)

    with pytest.raises(InvalidInputError, match="finite number"):
        solve_itinerary("humayuns-tomb", float("inf"), bundled_matrix)


def test_input_validation_visit_durations(bundled_matrix: TravelMatrix):
    """Negative, NaN, or infinite visit durations raise InvalidInputError."""
    with pytest.raises(InvalidInputError, match="cannot be negative"):
        solve_itinerary(
            "humayuns-tomb",
            120.0,
            bundled_matrix,
            visit_durations={"humayuns-tomb": -15.0},
        )

    with pytest.raises(InvalidInputError, match="finite number"):
        solve_itinerary(
            "humayuns-tomb",
            120.0,
            bundled_matrix,
            visit_durations={"humayuns-tomb": float("nan")},
        )


def test_input_validation_time_limit(bundled_matrix: TravelMatrix):
    """Non-positive, NaN, or infinite solver time limits raise InvalidInputError."""
    with pytest.raises(InvalidInputError, match="positive finite number"):
        solve_itinerary("humayuns-tomb", 120.0, bundled_matrix, time_limit_seconds=0)

    with pytest.raises(InvalidInputError, match="positive finite number"):
        solve_itinerary("humayuns-tomb", 120.0, bundled_matrix, time_limit_seconds=float("nan"))


# ---------------------------------------------------------------------------
# Honest OR-Tools Search Outcomes Tests
# ---------------------------------------------------------------------------


def test_honest_search_outcome_timeout(bundled_matrix: TravelMatrix):
    """When solver times out without finding solution, status reflects TIMEOUT honestly."""
    with (
        patch("ortools.constraint_solver.pywrapcp.RoutingModel.SolveWithParameters", return_value=None),
        patch("ortools.constraint_solver.pywrapcp.RoutingModel.status", return_value=routing_enums_pb2.RoutingSearchStatus.ROUTING_FAIL_TIMEOUT),
    ):
        itinerary = solve_itinerary("humayuns-tomb", 240.0, bundled_matrix, time_limit_seconds=1)
        assert itinerary.is_feasible is False
        assert itinerary.solver_status == "TIMEOUT"
        assert "timed out" in itinerary.status_message.lower()


def test_honest_search_outcome_proven_infeasible(bundled_matrix: TravelMatrix):
    """When solver proves problem is infeasible, status reflects INFEASIBLE honestly."""
    with (
        patch("ortools.constraint_solver.pywrapcp.RoutingModel.SolveWithParameters", return_value=None),
        patch("ortools.constraint_solver.pywrapcp.RoutingModel.status", return_value=routing_enums_pb2.RoutingSearchStatus.ROUTING_INFEASIBLE),
    ):
        itinerary = solve_itinerary("humayuns-tomb", 240.0, bundled_matrix)
        assert itinerary.is_feasible is False
        assert itinerary.solver_status == "INFEASIBLE"
        assert "proven infeasible" in itinerary.status_message.lower()
