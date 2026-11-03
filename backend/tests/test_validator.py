"""Tests for the independent RouteValidator: recalculation, budget overflow, duplicates, and impossible transitions."""

from __future__ import annotations

import pytest

from app.planner.matrix import load_matrix
from app.planner.models import Itinerary, Stop, TravelMatrix
from app.planner.solver import solve_itinerary
from app.planner.validator import RouteValidator, validate_itinerary


@pytest.fixture
def matrix() -> TravelMatrix:
    """Precomputed 15-monument driving matrix."""
    return load_matrix(profile="driving-car")


def test_valid_itinerary_passes_independent_validation(matrix: TravelMatrix):
    """Verify that a genuine solver itinerary passes all validation checks."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=240.0,
        matrix=matrix,
    )
    result = validate_itinerary(itinerary, matrix)

    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.recalculated_total_time_min == itinerary.total_time_min
    assert result.recalculated_total_time_min <= 240.0
    assert result.recalculated_travel_time_min > 0.0
    assert result.recalculated_visit_time_min > 0.0


def test_budget_overflow_detected(matrix: TravelMatrix):
    """Tampered itinerary exceeding time budget must fail independent validation."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=240.0,
        matrix=matrix,
    )

    # Artificially tighten budget below recalculated total time
    too_small_budget = itinerary.total_time_min - 20.0
    validator = RouteValidator(matrix)
    result = validator.validate(itinerary, time_budget_minutes=too_small_budget)

    assert result.is_valid is False
    assert any("Budget exceeded" in e for e in result.errors)


def test_solver_total_time_mismatch_detected(matrix: TravelMatrix):
    """If solver reported total time is tampered or fabricated, validator flags mismatch."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=240.0,
        matrix=matrix,
    )

    # Tamper the reported total time
    tampered_itinerary = Itinerary(
        is_feasible=itinerary.is_feasible,
        status_message=itinerary.status_message,
        start_monument=itinerary.start_monument,
        time_budget_min=itinerary.time_budget_min,
        total_time_min=itinerary.total_time_min - 50.0,  # Fabricated lower total
        total_travel_time_min=itinerary.total_travel_time_min,
        total_visit_time_min=itinerary.total_visit_time_min,
        total_travel_distance_m=itinerary.total_travel_distance_m,
        stops=itinerary.stops,
        profile=itinerary.profile,
        return_to_start=itinerary.return_to_start,
    )

    result = validate_itinerary(tampered_itinerary, matrix)
    assert result.is_valid is False
    assert any("does not match independently recalculated total time" in e for e in result.errors)


def test_solver_travel_time_mismatch_detected(matrix: TravelMatrix):
    """If solver reported travel time is independently tampered, validator flags mismatch."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=240.0,
        matrix=matrix,
    )

    tampered_itinerary = Itinerary(
        is_feasible=itinerary.is_feasible,
        status_message=itinerary.status_message,
        start_monument=itinerary.start_monument,
        time_budget_min=itinerary.time_budget_min,
        total_time_min=itinerary.total_time_min,
        total_travel_time_min=itinerary.total_travel_time_min + 30.0,  # Tampered travel time
        total_visit_time_min=itinerary.total_visit_time_min,
        total_travel_distance_m=itinerary.total_travel_distance_m,
        stops=itinerary.stops,
        profile=itinerary.profile,
        return_to_start=itinerary.return_to_start,
    )

    result = validate_itinerary(tampered_itinerary, matrix)
    assert result.is_valid is False
    assert any("does not match independently recalculated travel time" in e for e in result.errors)


def test_solver_visit_time_mismatch_detected(matrix: TravelMatrix):
    """If solver reported visit time is independently tampered, validator flags mismatch."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=240.0,
        matrix=matrix,
    )

    tampered_itinerary = Itinerary(
        is_feasible=itinerary.is_feasible,
        status_message=itinerary.status_message,
        start_monument=itinerary.start_monument,
        time_budget_min=itinerary.time_budget_min,
        total_time_min=itinerary.total_time_min,
        total_travel_time_min=itinerary.total_travel_time_min,
        total_visit_time_min=itinerary.total_visit_time_min - 45.0,  # Tampered visit time
        total_travel_distance_m=itinerary.total_travel_distance_m,
        stops=itinerary.stops,
        profile=itinerary.profile,
        return_to_start=itinerary.return_to_start,
    )

    result = validate_itinerary(tampered_itinerary, matrix)
    assert result.is_valid is False
    assert any("does not match independently recalculated visit time" in e for e in result.errors)


def test_solver_distance_mismatch_detected(matrix: TravelMatrix):
    """If solver reported travel distance is independently tampered, validator flags mismatch."""
    itinerary = solve_itinerary(
        start_monument="humayuns-tomb",
        time_budget_minutes=240.0,
        matrix=matrix,
    )

    tampered_itinerary = Itinerary(
        is_feasible=itinerary.is_feasible,
        status_message=itinerary.status_message,
        start_monument=itinerary.start_monument,
        time_budget_min=itinerary.time_budget_min,
        total_time_min=itinerary.total_time_min,
        total_travel_time_min=itinerary.total_travel_time_min,
        total_visit_time_min=itinerary.total_visit_time_min,
        total_travel_distance_m=itinerary.total_travel_distance_m + 5000.0,  # Tampered distance
        stops=itinerary.stops,
        profile=itinerary.profile,
        return_to_start=itinerary.return_to_start,
    )

    result = validate_itinerary(tampered_itinerary, matrix)
    assert result.is_valid is False
    assert any("does not match independently recalculated travel distance" in e for e in result.errors)


def test_duplicate_visits_detected_in_open_tour(matrix: TravelMatrix):
    """An open tour containing duplicate visits must fail validation."""
    dup_stops = [
        Stop(
            monument_slug="humayuns-tomb",
            name="Humayun's Tomb",
            arrival_time_min=0.0,
            visit_duration_min=60.0,
            departure_time_min=60.0,
            travel_time_to_next_min=10.0,
            travel_distance_to_next_m=3000.0,
        ),
        Stop(
            monument_slug="purana-qila",
            name="Purana Qila",
            arrival_time_min=70.0,
            visit_duration_min=60.0,
            departure_time_min=130.0,
            travel_time_to_next_min=10.0,
            travel_distance_to_next_m=3000.0,
        ),
        Stop(
            monument_slug="humayuns-tomb",  # Forbidden duplicate in open tour
            name="Humayun's Tomb",
            arrival_time_min=140.0,
            visit_duration_min=60.0,
            departure_time_min=200.0,
        ),
    ]

    itinerary = Itinerary(
        is_feasible=True,
        status_message="Test duplicate",
        start_monument="humayuns-tomb",
        time_budget_min=300.0,
        total_time_min=200.0,
        total_travel_time_min=20.0,
        total_visit_time_min=180.0,
        total_travel_distance_m=6000.0,
        stops=dup_stops,
        return_to_start=False,
    )

    result = validate_itinerary(itinerary, matrix)
    assert result.is_valid is False
    assert any("Forbidden duplicate visits" in e for e in result.errors)


def test_nonexistent_location_detected(matrix: TravelMatrix):
    """A stop with a non-existent slug must fail validation."""
    stops = [
        Stop(
            monument_slug="humayuns-tomb",
            name="Humayun's Tomb",
            arrival_time_min=0.0,
            visit_duration_min=60.0,
            departure_time_min=60.0,
            travel_time_to_next_min=10.0,
            travel_distance_to_next_m=2000.0,
        ),
        Stop(
            monument_slug="fantasy-citadel",  # Does not exist
            name="Fantasy Citadel",
            arrival_time_min=70.0,
            visit_duration_min=60.0,
            departure_time_min=130.0,
        ),
    ]

    itinerary = Itinerary(
        is_feasible=True,
        status_message="Test fantasy",
        start_monument="humayuns-tomb",
        time_budget_min=200.0,
        total_time_min=130.0,
        total_travel_time_min=10.0,
        total_visit_time_min=120.0,
        total_travel_distance_m=2000.0,
        stops=stops,
    )

    result = validate_itinerary(itinerary, matrix)
    assert result.is_valid is False
    assert any("not an existing or valid monument" in e for e in result.errors)


def test_timeline_progression_mismatch(matrix: TravelMatrix):
    """Gaps or mismatched departure/arrival times must fail validation."""
    stops = [
        Stop(
            monument_slug="humayuns-tomb",
            name="Humayun's Tomb",
            arrival_time_min=0.0,
            visit_duration_min=60.0,
            departure_time_min=60.0,
            travel_time_to_next_min=matrix.get_travel_time_minutes("humayuns-tomb", "purana-qila"),
            travel_distance_to_next_m=matrix.get_travel_distance_meters("humayuns-tomb", "purana-qila"),
        ),
        Stop(
            monument_slug="purana-qila",
            name="Purana Qila",
            arrival_time_min=999.0,  # Corrupted arrival time
            visit_duration_min=60.0,
            departure_time_min=1059.0,
        ),
    ]

    itinerary = Itinerary(
        is_feasible=True,
        status_message="Test gap",
        start_monument="humayuns-tomb",
        time_budget_min=2000.0,
        total_time_min=1059.0,
        total_travel_time_min=10.0,
        total_visit_time_min=120.0,
        total_travel_distance_m=2000.0,
        stops=stops,
    )

    result = validate_itinerary(itinerary, matrix)
    assert result.is_valid is False
    assert any("arrival mismatch" in e for e in result.errors)


def test_impossible_fabricated_transition_detected():
    """An impossible transition (e.g. 100km in 1 minute, > 150 km/h) fails validation."""
    locations = [[77.25, 28.59], [78.04, 27.17]]
    # Superluminal driving matrix
    matrix_fabricated = TravelMatrix(
        profile="driving-car",
        monument_slugs=["humayuns-tomb", "taj-mahal"],
        locations=locations,
        durations=[[0.0, 60.0], [60.0, 0.0]],  # 200 km in 60 seconds = 12000 km/h
        distances=[[0.0, 200000.0], [200000.0, 0.0]],
        created_at="2026-11-02T16:00:00Z",
    )

    stops = [
        Stop(
            monument_slug="humayuns-tomb",
            name="Humayun's Tomb",
            arrival_time_min=0.0,
            visit_duration_min=60.0,
            departure_time_min=60.0,
            travel_time_to_next_min=1.0,
            travel_distance_to_next_m=200000.0,
        ),
        Stop(
            monument_slug="taj-mahal",
            name="Taj Mahal",
            arrival_time_min=61.0,
            visit_duration_min=60.0,
            departure_time_min=121.0,
        ),
    ]

    itinerary = Itinerary(
        is_feasible=True,
        status_message="Test supersonic",
        start_monument="humayuns-tomb",
        time_budget_min=200.0,
        total_time_min=121.0,
        total_travel_time_min=1.0,
        total_visit_time_min=120.0,
        total_travel_distance_m=200000.0,
        stops=stops,
    )

    result = validate_itinerary(itinerary, matrix_fabricated)
    assert result.is_valid is False
    assert any("Implausible driving speed" in e for e in result.errors)

