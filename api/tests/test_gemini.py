import json
from unittest.mock import patch

import pytest
from app.planner.models import Itinerary, Stop

from app.services.gemini import GeminiService


@pytest.fixture
def sample_itinerary():
    return Itinerary(
        is_feasible=True,
        status_message="Optimal tour found within budget.",
        start_monument="humayuns-tomb",
        time_budget_min=240.0,
        total_time_min=180.0,
        total_travel_time_min=30.0,
        total_visit_time_min=150.0,
        total_travel_distance_m=12500.0,
        stops=[
            Stop(
                monument_slug="humayuns-tomb",
                name="Humayun's Tomb",
                arrival_time_min=0.0,
                visit_duration_min=60.0,
                departure_time_min=60.0,
                travel_time_to_next_min=15.0,
                travel_distance_to_next_m=6000.0,
            ),
            Stop(
                monument_slug="purana-qila",
                name="Purana Qila",
                arrival_time_min=75.0,
                visit_duration_min=45.0,
                departure_time_min=120.0,
                travel_time_to_next_min=15.0,
                travel_distance_to_next_m=6500.0,
            ),
            Stop(
                monument_slug="red-fort",
                name="Red Fort",
                arrival_time_min=135.0,
                visit_duration_min=45.0,
                departure_time_min=180.0,
            ),
        ],
        profile="driving-car",
        return_to_start=False,
        solver_status="SUCCESS",
    )


def test_heuristic_preference_parsing():
    """Verify rule-based fallback parses common natural language queries accurately."""
    service = GeminiService(api_key="test-key")
    parsed = service.parse_preferences("I want a 4 hours tour in Delhi starting at Humayun's Tomb, and visit Purana Qila")

    assert parsed.start_monument == "humayuns-tomb"
    assert parsed.time_budget_minutes == 240.0
    assert "purana-qila" in parsed.must_visit
    assert parsed.preferences.get("city") == "Delhi"
    assert parsed.profile == "driving-car"


def test_heuristic_walking_and_loop_parsing():
    """Verify walking profile and round trip detection."""
    service = GeminiService(api_key="test-key")
    parsed = service.parse_preferences("A walking tour around Taj Mahal for 90 minutes round trip")

    assert parsed.start_monument == "taj-mahal"
    assert parsed.time_budget_minutes == 90.0
    assert parsed.profile == "foot-walking"
    assert parsed.return_to_start is True


def test_gemini_api_parsing_with_mock():
    """Verify Gemini API response is properly extracted when API returns JSON."""
    service = GeminiService(api_key="valid-mock-key")
    gemini_payload = {
        "start_monument": "red-fort",
        "time_budget_minutes": 180,
        "must_visit": ["jama-masjid"],
        "city": "Delhi",
        "profile": "foot-walking",
        "return_to_start": False,
        "max_stops": 3,
    }

    with patch.object(service, "_call_gemini", return_value=json.dumps(gemini_payload)):
        parsed = service.parse_preferences("Walk around Red Fort for 3 hours")
        assert parsed.start_monument == "red-fort"
        assert parsed.time_budget_minutes == 180.0
        assert parsed.must_visit == ["jama-masjid"]
        assert parsed.preferences == {"city": "Delhi"}
        assert parsed.profile == "foot-walking"
        assert parsed.max_stops == 3


def test_gemini_api_failure_falls_back_to_heuristics():
    """If Gemini API fails with an exception, heuristic parser takes over gracefully."""
    service = GeminiService(api_key="valid-mock-key")
    with patch.object(service, "_call_gemini", side_effect=RuntimeError("Gemini API 500 error")):
        parsed = service.parse_preferences("3 hours tour starting at Taj Mahal")
        assert parsed.start_monument == "taj-mahal"
        assert parsed.time_budget_minutes == 180.0


def test_explain_itinerary_with_mock(sample_itinerary):
    """Verify explanation generation calls Gemini and returns narrative."""
    service = GeminiService(api_key="valid-mock-key")
    mock_narrative = "This tour starts at Humayun's Tomb, takes you to Purana Qila, and finishes at the majestic Red Fort."

    with patch.object(service, "_call_gemini", return_value=mock_narrative) as mock_call:
        narrative = service.explain_itinerary(sample_itinerary)
        assert narrative == mock_narrative
        mock_call.assert_called_once()
        # Verify the prompt contained the exact stops
        prompt_arg = mock_call.call_args[0][0]
        assert "Humayun's Tomb" in prompt_arg
        assert "Purana Qila" in prompt_arg
        assert "Red Fort" in prompt_arg


def test_explain_infeasible_itinerary():
    """Infeasible itineraries produce a clear refusal without hallucinating a tour."""
    service = GeminiService(api_key="test-key")
    infeasible = Itinerary(
        is_feasible=False,
        status_message="Proven infeasible: no route can satisfy time budget.",
        start_monument="taj-mahal",
        time_budget_min=30.0,
        total_time_min=0.0,
        total_travel_time_min=0.0,
        total_visit_time_min=0.0,
        total_travel_distance_m=0.0,
        stops=[],
        solver_status="INFEASIBLE",
    )
    explanation = service.explain_itinerary(infeasible)
    assert "No feasible itinerary could be constructed" in explanation
    assert "INFEASIBLE" in explanation


def test_fallback_explanation_when_gemini_unavailable(sample_itinerary):
    """Fallback explanation provides informative details when Gemini is unconfigured or fails."""
    service = GeminiService(api_key="unconfigured")
    with patch.object(service, "_call_gemini", side_effect=RuntimeError("Network down")):
        narrative = service.explain_itinerary(sample_itinerary)
        assert "Humayun's Tomb" in narrative
        assert "Red Fort" in narrative
        assert "3 monuments" in narrative
        assert "180.0 mins" in narrative or "3h 0m" in narrative
