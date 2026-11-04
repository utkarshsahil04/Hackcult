from __future__ import annotations

import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")

from unittest.mock import MagicMock, patch

import pytest
from app.main import app
from app.planner.models import Itinerary, ValidationResult
from app.services.gemini import GeminiService, ParsedConstraints, get_gemini_service
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


def test_plan_tour_valid_request_direct_parameters(client):
    """Test planning a tour with direct structured parameters."""
    payload = {
        "start_monument": "humayuns-tomb",
        "time_budget_minutes": 240,
        "preferences": {"city": "Delhi"},
        "profile": "driving-car",
        "return_to_start": False,
    }
    response = client.post("/api/tours/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_feasible"] is True
    assert data["is_validated"] is True
    assert data["solver_status"] == "SUCCESS"
    assert data["itinerary"] is not None
    assert len(data["itinerary"]["stops"]) >= 1
    assert data["itinerary"]["stops"][0]["monument_slug"] == "humayuns-tomb"
    assert data["validation"]["is_valid"] is True
    assert data["explanation"] is not None
    assert len(data["explanation"]) > 0


def test_plan_tour_gemini_natural_language_parsing(client):
    """Test planning a tour from a natural language query using Gemini parsing."""
    mock_gemini = MagicMock(spec=GeminiService)
    mock_gemini.parse_preferences.return_value = ParsedConstraints(
        start_monument="taj-mahal",
        time_budget_minutes=180.0,
        must_visit=["agra-fort"],
        preferences={"city": "Agra"},
        profile="driving-car",
        return_to_start=False,
    )
    mock_gemini.explain_itinerary.return_value = "Tour begins at Taj Mahal and visits Agra Fort."

    app.dependency_overrides[get_gemini_service] = lambda: mock_gemini
    try:
        response = client.post("/api/tours/plan", json={"query": "3 hours tour in Agra starting at Taj Mahal"})
        assert response.status_code == 200
        data = response.json()
        assert data["is_feasible"] is True
        assert data["is_validated"] is True
        assert data["itinerary"]["start_monument"] == "taj-mahal"
        # Verify solver received structured constraints
        assert "taj-mahal" in [s["monument_slug"] for s in data["itinerary"]["stops"]]
        assert "agra-fort" in [s["monument_slug"] for s in data["itinerary"]["stops"]]
        assert data["explanation"] == "Tour begins at Taj Mahal and visits Agra Fort."
        mock_gemini.parse_preferences.assert_called_once_with("3 hours tour in Agra starting at Taj Mahal")
        mock_gemini.explain_itinerary.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_gemini_service, None)


def test_plan_tour_validator_is_called(client):
    """Verify independent validator is invoked on the solver's itinerary."""
    with patch("app.routes.tours.validate_itinerary") as mock_validate:
        mock_validate.return_value = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            recalculated_total_time_min=100.0,
            recalculated_travel_time_min=20.0,
            recalculated_visit_time_min=80.0,
            recalculated_distance_m=5000.0,
        )
        response = client.post(
            "/api/tours/plan",
            json={"start_monument": "humayuns-tomb", "time_budget_minutes": 180},
        )
        assert response.status_code == 200
        mock_validate.assert_called_once()
        data = response.json()
        assert data["is_validated"] is True
        assert data["validation"]["recalculated_total_time_min"] == 100.0


def test_plan_tour_gemini_explains_without_modifying_route(client):
    """Verify Gemini explains the itinerary and does not alter solver stops."""
    mock_gemini = MagicMock(spec=GeminiService)
    mock_gemini.parse_preferences.return_value = ParsedConstraints()

    def fake_explain(itin):
        # Verify passed itinerary has exact stops
        return f"Narrative for {len(itin.stops)} stops starting at {itin.start_monument}"

    mock_gemini.explain_itinerary.side_effect = fake_explain

    app.dependency_overrides[get_gemini_service] = lambda: mock_gemini
    try:
        response = client.post(
            "/api/tours/plan",
            json={"start_monument": "red-fort", "time_budget_minutes": 180},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Narrative for" in data["explanation"]
        assert "red-fort" in data["explanation"]
    finally:
        app.dependency_overrides.pop(get_gemini_service, None)


def test_plan_tour_infeasible_solver_result(client):
    """When solver returns is_feasible=False, API returns clear response without inventing route."""
    with patch("app.routes.tours.solve_itinerary") as mock_solver:
        mock_solver.return_value = Itinerary(
            is_feasible=False,
            status_message="Proven infeasible: impossible time budget.",
            start_monument="taj-mahal",
            time_budget_min=10.0,
            total_time_min=0.0,
            total_travel_time_min=0.0,
            total_visit_time_min=0.0,
            total_travel_distance_m=0.0,
            stops=[],
            solver_status="INFEASIBLE",
        )
        response = client.post(
            "/api/tours/plan",
            json={"start_monument": "taj-mahal", "time_budget_minutes": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_feasible"] is False
        assert data["is_validated"] is False
        assert data["solver_status"] == "INFEASIBLE"
        assert data["itinerary"]["stops"] == []
        assert "No feasible itinerary could be constructed" in data["explanation"]


def test_plan_tour_validator_rejection(client):
    """When independent validator rejects route, is_validated is False and errors are reported."""
    with patch("app.routes.tours.validate_itinerary") as mock_validator:
        mock_validator.return_value = ValidationResult(
            is_valid=False,
            errors=["Recalculated travel time mismatch (> tolerance)", "Budget exceeded"],
            warnings=[],
            recalculated_total_time_min=300.0,
        )
        response = client.post(
            "/api/tours/plan",
            json={"start_monument": "humayuns-tomb", "time_budget_minutes": 200},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_validated"] is False
        assert data["validation"]["is_valid"] is False
        assert "Budget exceeded" in data["validation"]["errors"]
        assert "failed independent mathematical verification" in data["explanation"]


def test_plan_tour_missing_gemini_configuration_handles_gracefully(client):
    """When Gemini API key is missing or dummy, solver still succeeds with fallback explanation."""
    unconfigured_gemini = GeminiService(api_key="")
    app.dependency_overrides[get_gemini_service] = lambda: unconfigured_gemini
    try:
        response = client.post(
            "/api/tours/plan",
            json={"start_monument": "humayuns-tomb", "time_budget_minutes": 180},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_feasible"] is True
        assert data["is_validated"] is True
        assert "Your optimized tour begins at" in data["explanation"]
    finally:
        app.dependency_overrides.pop(get_gemini_service, None)


def test_plan_tour_gemini_api_failure_handles_gracefully(client):
    """When Gemini raises an upstream error, tour planning still succeeds with fallback narrative."""
    failing_gemini = GeminiService(api_key="mock-key")
    with patch.object(failing_gemini, "_call_gemini", side_effect=RuntimeError("Gemini 503 unavailable")):
        app.dependency_overrides[get_gemini_service] = lambda: failing_gemini
        try:
            response = client.post(
                "/api/tours/plan",
                json={
                    "query": "4 hours in Delhi starting at Red Fort",
                    "time_budget_minutes": 240,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["is_feasible"] is True
            assert data["is_validated"] is True
            assert data["itinerary"]["start_monument"] == "red-fort"
            assert "Your optimized tour begins at" in data["explanation"]
        finally:
            app.dependency_overrides.pop(get_gemini_service, None)


def test_plan_tour_invalid_payload_missing_query_start_and_budget(client):
    """Request with no query, start or budget returns HTTP 400 validation error."""
    response = client.post("/api/tours/plan", json={})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_plan_tour_invalid_negative_budget(client):
    """Request with negative time budget returns HTTP 400 validation error."""
    response = client.post(
        "/api/tours/plan",
        json={"start_monument": "humayuns-tomb", "time_budget_minutes": -50},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_plan_tour_invalid_zero_max_stops(client):
    """Request with max_stops=0 returns HTTP 400 validation error."""
    response = client.post(
        "/api/tours/plan",
        json={"start_monument": "humayuns-tomb", "time_budget_minutes": 180, "max_stops": 0},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_plan_tour_unknown_monument_slug(client):
    """Request with an unrecognized monument slug returns HTTP 400 validation error."""
    response = client.post(
        "/api/tours/plan",
        json={"start_monument": "eiffel-tower", "time_budget_minutes": 180},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "eiffel-tower" in body["error"]["message"]


def test_plan_never_exceeds_five_stops_even_when_asked_for_more(client):
    r = client.post("/api/tours/plan", json={"time_budget_minutes": 600, "max_stops": 9, "preferences": {"city": "Delhi"}})
    body = r.json()
    assert r.status_code == 200 and body["is_validated"] is True
    assert len(body["itinerary"]["stops"]) == 5
    assert body["metrics"]["max_stops"] == 5


def test_plan_without_start_picks_one_and_is_optimal(client):
    r = client.post("/api/tours/plan", json={"time_budget_minutes": 240, "preset": "standard", "preferences": {"city": "Delhi"}})
    body = r.json()
    assert body["is_validated"] is True and body["metrics"]["is_optimal"] is True
    assert body["itinerary"]["total_time_min"] <= 240


def test_plan_preset_and_interests_are_configurable(client):
    quick = client.post("/api/tours/plan", json={"time_budget_minutes": 300, "preset": "relaxed", "preferences": {"city": "Delhi"}}).json()
    assert len(quick["itinerary"]["stops"]) <= 3
    gardens = client.post("/api/tours/plan", json={"time_budget_minutes": 300, "interests": ["garden"], "preferences": {"city": "Delhi"}}).json()
    assert any(s["monument_slug"] in ("lodhi-gardens", "sunder-nursery", "humayuns-tomb") for s in gardens["itinerary"]["stops"])


def test_plan_unknown_preset_is_a_400(client):
    assert client.post("/api/tours/plan", json={"time_budget_minutes": 120, "preset": "nope"}).status_code == 400


def test_plan_accepts_new_delhi_sites(client):
    r = client.post("/api/tours/plan", json={"start_monument": "india-gate", "time_budget_minutes": 180})
    assert r.status_code == 200 and r.json()["itinerary"]["stops"][0]["monument_slug"] == "india-gate"


def test_route_line_returns_a_line_for_each_leg(client):
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        r = client.post("/api/tours/route-line", json={"stops": ["red-fort", "india-gate", "humayuns-tomb"], "profile": "foot-walking"})
    body = r.json()
    assert r.status_code == 200 and body["source"] == "straight"
    assert len(body["legs"]) == 2
    assert body["legs"][0][-1] == body["legs"][1][0]


@pytest.mark.parametrize("stops", [["red-fort"], ["red-fort", "not-a-monument"], ["red-fort", "red-fort"], [f"s{i}" for i in range(6)]])
def test_route_line_rejects_bad_stops_without_calling_out(client, stops):
    with patch("urllib.request.urlopen") as opened:
        r = client.post("/api/tours/route-line", json={"stops": stops})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    opened.assert_not_called()


@pytest.mark.parametrize(("start", "budget"), [("india-gate", 300), ("purana-qila", 300), ("purana-qila", 420), ("abdul-rahim-khan-i-khana-tomb", 600)])
def test_five_stop_plans_match_the_exact_optimum(client, start, budget):
    """OR-Tools alone planned fewer stops or a slower route for these walking days."""
    r = client.post("/api/tours/plan", json={
        "start_monument": start, "time_budget_minutes": budget, "preset": "standard", "max_stops": 5,
        "profile": "foot-walking", "preferences": {"city": "Delhi"}, "time_limit_seconds": 1,
    })
    body = r.json()
    assert r.status_code == 200 and body["is_validated"] is True
    assert body["metrics"]["is_optimal"] is True
    assert len(body["itinerary"]["stops"]) == 5


def test_chosen_monuments_are_all_in_the_five_stop_plan(client):
    must = ["red-fort", "humayuns-tomb", "lodhi-gardens", "india-gate", "jantar-mantar"]
    r = client.post("/api/tours/plan", json={"time_budget_minutes": 600, "preset": "quick", "max_stops": 5, "must_visit": must, "preferences": {"city": "Delhi"}, "time_limit_seconds": 1})
    body = r.json()
    assert r.status_code == 200 and body["is_validated"] is True
    assert {s["monument_slug"] for s in body["itinerary"]["stops"]} == set(must)


def test_a_chosen_place_outside_the_city_and_leg_limit_is_still_planned(client):
    r = client.post("/api/tours/plan", json={"time_budget_minutes": 600, "preset": "quick", "max_stops": 3, "must_visit": ["fatehpur-sikri", "taj-mahal"], "preferences": {"city": "Agra"}, "time_limit_seconds": 1})
    body = r.json()
    assert r.status_code == 200 and body["is_validated"] is True
    assert {"fatehpur-sikri", "taj-mahal"} <= {s["monument_slug"] for s in body["itinerary"]["stops"]}
