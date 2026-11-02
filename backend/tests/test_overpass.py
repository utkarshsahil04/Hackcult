"""Tests for Overpass POI parsing, deduplication, caching, expiry, and offline mode."""

from __future__ import annotations

import json
import urllib.error
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from app.planner.models import POI, CacheNotFoundError, OverpassError
from app.planner.overpass import (
    categorize_tags,
    fetch_pois_for_monuments,
    is_cache_fresh,
    load_overpass_cache,
    parse_overpass_response,
    save_overpass_cache,
)


@pytest.fixture
def sample_overpass_payload() -> dict:
    """Fixture providing a realistic Overpass API JSON response."""
    return {
        "version": 0.6,
        "generator": "Overpass API",
        "elements": [
            {
                "type": "node",
                "id": 1001,
                "lat": 28.5919,
                "lon": 77.2478,
                "tags": {
                    "name": "Isa Khan Tomb",
                    "historic": "tomb",
                },
            },
            {
                "type": "way",
                "id": 2001,
                "center": {"lat": 28.5908, "lon": 77.2435},
                "tags": {
                    "name": "Mirza Ghalib Museum",
                    "tourism": "museum",
                },
            },
            {
                "type": "node",
                "id": 1002,
                "lat": 28.5902,
                "lon": 77.2430,
                "tags": {
                    "name": "Al-Quresh Food Point",
                    "amenity": "restaurant",
                },
            },
            {
                "type": "node",
                "id": 1003,
                "lat": 28.5910,
                "lon": 77.2432,
                "tags": {
                    "name": "Nizamuddin Crafts",
                    "shop": "craft",
                },
            },
            {
                "type": "node",
                "id": 1004,
                "lat": 28.5915,
                "lon": 77.2438,
                "tags": {
                    "name": "Dargah Central Market",
                    "amenity": "marketplace",
                },
            },
            {
                "type": "node",
                "id": 1005,
                "lat": 28.5912,
                "lon": 77.2425,
                "tags": {
                    "name": "Nizamuddin Shrine Viewpoint",
                    "tourism": "viewpoint",
                },
            },
            # Duplicate of node 1001 to test deduplication
            {
                "type": "node",
                "id": 1001,
                "lat": 28.5919,
                "lon": 77.2478,
                "tags": {
                    "name": "Isa Khan Tomb Duplicate",
                    "historic": "tomb",
                },
            },
            # Unnamed node: should be discarded
            {
                "type": "node",
                "id": 9999,
                "lat": 28.5920,
                "lon": 77.2480,
                "tags": {
                    "historic": "bench",
                },
            },
            # Node with empty name string: should be discarded
            {
                "type": "node",
                "id": 9998,
                "lat": 28.5921,
                "lon": 77.2481,
                "tags": {
                    "name": "   ",
                    "amenity": "waste_basket",
                },
            },
            # Element without coordinates: should be discarded
            {
                "type": "node",
                "id": 9997,
                "tags": {
                    "name": "No Coordinate POI",
                    "historic": "memorial",
                },
            },
        ],
    }


def test_overpass_response_parsing(sample_overpass_payload: dict):
    """Test response parsing, category assignment, and dropped invalid entries."""
    pois = parse_overpass_response(
        sample_overpass_payload,
        associated_monument="humayuns-tomb",
        monument_lat=28.59333,
        monument_lon=77.25083,
    )

    # 6 valid items (1001, 2001, 1002, 1003, 1004, 1005); duplicate and unnamed discarded
    assert len(pois) == 6

    names = {p.name for p in pois}
    assert "Isa Khan Tomb" in names
    assert "Mirza Ghalib Museum" in names
    assert "Al-Quresh Food Point" in names
    assert "No Coordinate POI" not in names
    assert "Isa Khan Tomb Duplicate" not in names

    # Check category mappings
    by_id = {p.osm_id: p for p in pois}
    assert by_id[1001].category == "historical"
    assert by_id[2001].category == "museum"
    assert by_id[1002].category == "food"
    assert by_id[1003].category == "handicrafts"
    assert by_id[1004].category == "market"
    assert by_id[1005].category == "cultural"

    # Check distance calculation
    for p in pois:
        assert p.distance_m is not None
        assert p.distance_m > 0
        assert p.associated_monument == "humayuns-tomb"


def test_overpass_tag_categorization():
    """Verify category resolution rules across multiple tag combinations."""
    assert categorize_tags({"tourism": "museum"}) == "museum"
    assert categorize_tags({"historic": "monument"}) == "historical"
    assert categorize_tags({"historic": "fort"}) == "historical"
    assert categorize_tags({"shop": "craft"}) == "handicrafts"
    assert categorize_tags({"shop": "antiques"}) == "handicrafts"
    assert categorize_tags({"amenity": "cafe"}) == "food"
    assert categorize_tags({"amenity": "restaurant"}) == "food"
    assert categorize_tags({"amenity": "marketplace"}) == "market"
    assert categorize_tags({"shop": "mall"}) == "market"
    assert categorize_tags({"tourism": "gallery"}) == "cultural"
    assert categorize_tags({"amenity": "place_of_worship"}) == "cultural"


def test_malformed_overpass_response_raises():
    """Verify that an invalid Overpass response raises OverpassError."""
    with pytest.raises(OverpassError, match="missing 'elements'"):
        parse_overpass_response({"invalid": "structure"})


def test_poi_deduplication(sample_overpass_payload: dict):
    """Verify deduplication removes repeated (osm_type, osm_id) records."""
    pois = parse_overpass_response(sample_overpass_payload)
    ids = [p.osm_id for p in pois]
    assert ids.count(1001) == 1


def test_cache_persistence_and_expiry(tmp_path: Path):
    """Test saving to disk, loading from disk, freshness check, and expiry."""
    cache_file = tmp_path / "cache" / "test_pois.json"
    poi = POI(
        name="Test Tomb",
        category="historical",
        latitude=28.5,
        longitude=77.2,
        osm_id=42,
        osm_type="node",
        associated_monument="test-monument",
        distance_m=120.5,
    )

    save_overpass_cache([poi], cache_path=cache_file, ttl_seconds=3600)
    assert cache_file.is_file()

    # Load cache back
    loaded = load_overpass_cache(cache_path=cache_file)
    assert len(loaded) == 1
    assert loaded[0].name == "Test Tomb"
    assert loaded[0].osm_id == 42
    assert loaded[0].distance_m == 120.5

    # Freshness check
    assert is_cache_fresh(cache_file, ttl_seconds=3600) is True

    # Simulate expired cache
    expired_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    raw = json.loads(cache_file.read_text(encoding="utf-8"))
    raw["fetched_at"] = expired_time
    cache_file.write_text(json.dumps(raw), encoding="utf-8")

    assert is_cache_fresh(cache_file, ttl_seconds=3600) is False
    with pytest.raises(OverpassError, match="Cache expired"):
        load_overpass_cache(cache_path=cache_file, require_fresh=True, ttl_seconds=3600)


def test_offline_mode_without_network(tmp_path: Path):
    """Verify offline mode never makes network calls and reads local cache."""
    cache_file = tmp_path / "offline_pois.json"
    poi = POI(
        name="Offline Heritage Site",
        category="historical",
        latitude=28.5,
        longitude=77.2,
        osm_id=99,
        osm_type="node",
    )
    save_overpass_cache([poi], cache_path=cache_file)

    with patch("urllib.request.urlopen") as mock_url:
        pois = fetch_pois_for_monuments(
            [{"slug": "test", "latitude": 28.5, "longitude": 77.2}],
            cache_path=cache_file,
            offline=True,
        )
        # urlopen MUST NOT be called in offline mode
        mock_url.assert_not_called()
        assert len(pois) == 1
        assert pois[0].name == "Offline Heritage Site"


def test_offline_mode_missing_cache_raises_explicit_error(tmp_path: Path):
    """In offline mode, if cache does not exist, raise CacheNotFoundError."""
    missing_path = tmp_path / "non_existent.json"
    with (
        patch("app.planner.overpass.BUNDLED_CACHE_PATH", tmp_path / "no_bundled.json"),
        pytest.raises(CacheNotFoundError, match="Overpass POI cache not found"),
    ):
        load_overpass_cache(cache_path=missing_path)


def test_network_failure_falls_back_to_cache(sample_overpass_payload: dict, tmp_path: Path):
    """When a network error occurs during live fetch, fall back to existing cache if available."""
    cache_file = tmp_path / "fallback_pois.json"
    cached_poi = POI(
        name="Cached Fallback POI",
        category="museum",
        latitude=28.5,
        longitude=77.2,
        osm_id=77,
        osm_type="node",
    )
    save_overpass_cache([cached_poi], cache_path=cache_file)

    # Force urllib to raise URLError
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        # force_refresh=True to attempt live fetch
        pois = fetch_pois_for_monuments(
            [{"slug": "test", "latitude": 28.5, "longitude": 77.2}],
            cache_path=cache_file,
            force_refresh=True,
        )
        assert len(pois) == 1
        assert pois[0].name == "Cached Fallback POI"


def test_network_failure_without_cache_raises(tmp_path: Path):
    """When live fetch fails and no cache exists, raise OverpassError."""
    cache_file = tmp_path / "no_cache.json"
    with (
        patch("app.planner.overpass.BUNDLED_CACHE_PATH", tmp_path / "no_bundled.json"),
        patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Timeout")),
        pytest.raises(OverpassError, match="Network error fetching POIs"),
    ):
        fetch_pois_for_monuments(
            [{"slug": "test", "latitude": 28.5, "longitude": 77.2}],
            cache_path=cache_file,
            force_refresh=True,
        )
