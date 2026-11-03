import pytest

from app.planner.config import (
    interest_priorities,
    preset_names,
    resolve_config,
    restrict_legs,
)
from app.planner.exhaustive import best_plan
from app.planner.models import InvalidInputError, TravelMatrix
from app.planner.solver import solve_itinerary
from app.planner.validator import validate_itinerary


def _matrix():
    m = 60.0
    return TravelMatrix(
        profile="driving-car",
        monument_slugs=["a", "b", "c", "d"],
        locations=[[77.0, 28.0], [77.1, 28.0], [77.2, 28.0], [77.3, 28.0]],
        durations=[[0, 10 * m, 20 * m, 90 * m], [10 * m, 0, 10 * m, 90 * m], [20 * m, 10 * m, 0, 90 * m], [90 * m, 90 * m, 90 * m, 0]],
        distances=[[0, 5000, 10000, 60000], [5000, 0, 5000, 60000], [10000, 5000, 0, 60000], [60000, 60000, 60000, 0]],
        created_at="2026-01-01T00:00:00Z",
    )


def test_every_preset_resolves_within_the_hard_cap():
    for name in preset_names():
        assert 1 <= resolve_config(name).max_stops <= 3


def test_request_cannot_exceed_three_stops():
    assert resolve_config("standard", max_stops=9).max_stops == 3
    assert resolve_config("standard", max_stops=1).max_stops == 1


def test_unknown_preset_is_rejected():
    with pytest.raises(InvalidInputError):
        resolve_config("nope")


def test_restrict_legs_makes_long_legs_unroutable_only():
    limited = restrict_legs(_matrix(), 30)
    assert limited.has_route("a", "b")
    assert not limited.has_route("a", "d")
    assert limited.get_travel_time_seconds("a", "a") == 0


def test_interest_priorities_count_keyword_matches():
    rows = [
        {"slug": "x", "name": "Lodhi Gardens", "era": "Sultanate", "architectural_style": "Garden tomb"},
        {"slug": "y", "name": "Fort", "era": "Mughal", "architectural_style": "Fort"},
    ]
    assert interest_priorities(rows, ["garden", "mughal"]) == {"x": 1, "y": 1}
    assert interest_priorities(rows, ["rajput"]) == {}


def test_best_plan_maximises_stops_then_minimises_time():
    visit = dict.fromkeys("abcd", 30.0)
    score, route = best_plan(_matrix(), 180, 3, visit, list("abcd"), start="a")
    assert route == ["a", "b", "c"]
    assert score == (3, -110.0)


def test_best_plan_returns_none_when_nothing_fits():
    assert best_plan(_matrix(), 10, 3, dict.fromkeys("abcd", 30.0), list("abcd")) is None


def test_best_plan_honours_must_visit_and_priority():
    visit = dict.fromkeys("abcd", 30.0)
    assert best_plan(_matrix(), 300, 2, visit, list("abcd"), start="a", must_visit={"d"})[1] == ["a", "d"]
    assert best_plan(_matrix(), 300, 2, visit, list("abcd"), start="a", priorities={"d": 2})[1] == ["a", "d"]


def test_solver_agrees_with_oracle_and_passes_validator_on_restricted_matrix():
    matrix = restrict_legs(_matrix(), 30)
    visit = dict.fromkeys("abcd", 30.0)
    itinerary = solve_itinerary("a", 180, matrix, max_stops=3, visit_durations=visit, time_limit_seconds=1)
    assert [s.monument_slug for s in itinerary.stops] == best_plan(matrix, 180, 3, visit, list("abcd"), start="a")[1]
    assert validate_itinerary(itinerary, matrix=matrix, time_budget_minutes=180, visit_durations=visit).is_valid


def test_solver_priorities_change_which_stop_is_kept():
    visit = dict.fromkeys("abcd", 30.0)
    itinerary = solve_itinerary("a", 300, _matrix(), max_stops=2, visit_durations=visit, time_limit_seconds=1, priorities={"d": 2})
    assert [s.monument_slug for s in itinerary.stops] == ["a", "d"]
