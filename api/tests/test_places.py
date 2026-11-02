import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")

from unittest.mock import patch

import pytest
from app.planner.models import CacheNotFoundError, OverpassError
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_nearby_places_success_by_monument(client):
    """Querying nearby places by monument slug returns cached places with HTTP 200."""
    response = client.get("/api/places/nearby?monument_slug=humayuns-tomb")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "name" in first
    assert "category" in first
    assert "latitude" in first
    assert "longitude" in first
    assert "osm_id" in first
    assert first["associated_monument"] == "humayuns-tomb"


def test_nearby_places_alias_monument_param(client):
    """Querying using 'monument' alias returns identical results to 'monument_slug'."""
    res1 = client.get("/api/places/nearby?monument_slug=humayuns-tomb")
    res2 = client.get("/api/places/nearby?monument=humayuns-tomb")
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json() == res2.json()


def test_nearby_places_success_by_coordinates(client):
    """Querying nearby places by lat/lon returns nearby places within radius."""
    # Near Humayun's Tomb: 28.5933, 77.2507
    response = client.get("/api/places/nearby?latitude=28.5933&longitude=77.2507&radius_m=1000")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Every returned place must be within 1000m
    for place in data:
        assert place["distance_m"] is not None
        assert place["distance_m"] <= 1000.0


def test_nearby_places_category_filter(client):
    """Filtering by category returns only places matching that category."""
    response = client.get("/api/places/nearby?monument_slug=humayuns-tomb&category=historical")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for place in data:
        assert place["category"] == "historical"


def test_nearby_places_empty_result_returns_200_and_empty_array(client):
    """When no places match the query, return HTTP 200 with an empty list."""
    response = client.get("/api/places/nearby?monument_slug=non-existent-monument-slug-xyz")
    assert response.status_code == 200
    assert response.json() == []


def test_nearby_places_empty_by_coordinates_returns_200_empty_array(client):
    """Coordinates in the middle of nowhere return HTTP 200 and []."""
    response = client.get("/api/places/nearby?latitude=0.0&longitude=0.0&radius_m=500")
    assert response.status_code == 200
    assert response.json() == []


def test_nearby_places_upstream_failure_returns_502(client):
    """If Overpass cache is missing or corrupt, returns HTTP 502 with UPSTREAM_PLACES_UNAVAILABLE."""
    with patch("app.routes.places.load_overpass_cache", side_effect=CacheNotFoundError("Cache missing")):
        response = client.get("/api/places/nearby?monument_slug=humayuns-tomb")
        assert response.status_code == 502
        body = response.json()
        assert "error" in body
        assert body["error"]["code"] == "UPSTREAM_PLACES_UNAVAILABLE"


def test_nearby_places_upstream_overpass_error_returns_502(client):
    """If OverpassError is raised, returns HTTP 502 with UPSTREAM_PLACES_UNAVAILABLE."""
    with patch("app.routes.places.load_overpass_cache", side_effect=OverpassError("Upstream failure")):
        response = client.get("/api/places/nearby?monument_slug=humayuns-tomb")
        assert response.status_code == 502
        body = response.json()
        assert body["error"]["code"] == "UPSTREAM_PLACES_UNAVAILABLE"


def test_nearby_places_invalid_partial_coordinates(client):
    """Passing only latitude without longitude returns HTTP 400 validation error."""
    response = client.get("/api/places/nearby?latitude=28.5")
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_nearby_places_invalid_out_of_range_coordinates(client):
    """Passing latitude > 90 returns HTTP 400 validation error."""
    response = client.get("/api/places/nearby?latitude=999.0&longitude=77.0")
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_nearby_places_invalid_negative_radius(client):
    """Passing negative radius returns HTTP 400 validation error."""
    response = client.get("/api/places/nearby?monument_slug=humayuns-tomb&radius_m=-100")
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
