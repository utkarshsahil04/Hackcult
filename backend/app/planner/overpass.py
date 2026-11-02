"""OpenStreetMap Overpass API client, response parser, deduplicator, and persistent cache."""

from __future__ import annotations

import json
import logging
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.planner.models import POI, CacheNotFoundError, OverpassError

logger = logging.getLogger(__name__)

DEFAULT_BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = DEFAULT_BACKEND_ROOT / "data" / "cache"
DEFAULT_CACHE_PATH = DEFAULT_CACHE_DIR / "overpass_pois.json"
BUNDLED_CACHE_PATH = Path(__file__).resolve().parent / "data" / "overpass_pois.json"

OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
DEFAULT_TTL_SECONDS = 7 * 24 * 3600  # 7 days
DEFAULT_RADIUS_METERS = 1000
DEFAULT_USER_AGENT = "RaaheinTourPlanner/1.0 (https://github.com/utkarshsahil04/Hackcult)"


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great Circle distance in meters between two coordinates."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 1)


def categorize_tags(tags: dict[str, str]) -> str:
    """Map OpenStreetMap tags to a high-level category."""
    tourism = tags.get("tourism", "").lower()
    historic = tags.get("historic", "").lower()
    amenity = tags.get("amenity", "").lower()
    shop = tags.get("shop", "").lower()

    if tourism == "museum" or tags.get("museum") is not None:
        return "museum"
    if historic in {
        "monument",
        "memorial",
        "archaeological_site",
        "castle",
        "ruins",
        "tomb",
        "fort",
        "city_gate",
    }:
        return "historical"
    if shop in {"craft", "antiques", "art", "souvenir"} or tags.get("craft"):
        return "handicrafts"
    if amenity in {"restaurant", "cafe", "fast_food", "food_court", "bar", "pub"}:
        return "food"
    if (
        shop in {"convenience", "supermarket", "mall", "department_store"}
        or amenity == "marketplace"
    ):
        return "market"
    if (
        tourism in {"artwork", "gallery", "viewpoint", "attraction"}
        or amenity in {"theatre", "arts_centre", "place_of_worship"}
    ):
        return "cultural"

    return "cultural"


def build_overpass_query(lat: float, lon: float, radius_m: int) -> str:
    """Construct an Overpass QL query searching for POIs around coordinates."""
    return f"""
    [out:json][timeout:25];
    (
      node["tourism"~"museum|artwork|gallery|viewpoint|attraction"](around:{radius_m},{lat},{lon});
      way["tourism"~"museum|artwork|gallery|viewpoint|attraction"](around:{radius_m},{lat},{lon});
      node["historic"~"monument|memorial|archaeological_site|castle|ruins|tomb|fort"](around:{radius_m},{lat},{lon});
      way["historic"~"monument|memorial|archaeological_site|castle|ruins|tomb|fort"](around:{radius_m},{lat},{lon});
      node["amenity"~"arts_centre|theatre|restaurant|cafe|food_court|marketplace"](around:{radius_m},{lat},{lon});
      way["amenity"~"arts_centre|theatre|restaurant|cafe|food_court|marketplace"](around:{radius_m},{lat},{lon});
      node["shop"~"craft|antiques|art|souvenir"](around:{radius_m},{lat},{lon});
      way["shop"~"craft|antiques|art|souvenir"](around:{radius_m},{lat},{lon});
    );
    out center tags;
    """


def parse_overpass_response(
    data: dict[str, Any],
    associated_monument: str = "",
    monument_lat: float | None = None,
    monument_lon: float | None = None,
) -> list[POI]:
    """Parse an Overpass JSON response, extract valid POIs, and deduplicate."""
    if not isinstance(data, dict) or "elements" not in data:
        raise OverpassError("Malformed Overpass response: missing 'elements' list")

    elements = data.get("elements", [])
    pois: list[POI] = []
    seen: set[tuple[str, int]] = set()

    for elem in elements:
        osm_type = str(elem.get("type", "node"))
        osm_id = elem.get("id")
        if osm_id is None:
            continue
        try:
            osm_id = int(osm_id)
        except (ValueError, TypeError):
            continue

        key = (osm_type, osm_id)
        if key in seen:
            continue

        tags = elem.get("tags")
        if not isinstance(tags, dict):
            continue

        name = tags.get("name") or tags.get("name:en")
        if not name or not str(name).strip():
            # Discard unnamed utility nodes or markers
            continue
        name = str(name).strip()

        # Determine coordinates (node has lat/lon, way/relation has center)
        lat = elem.get("lat")
        lon = elem.get("lon")
        if lat is None or lon is None:
            center = elem.get("center", {})
            lat = center.get("lat")
            lon = center.get("lon")

        if lat is None or lon is None:
            continue

        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError):
            continue

        dist_m: float | None = None
        if monument_lat is not None and monument_lon is not None:
            dist_m = haversine_distance(monument_lat, monument_lon, lat, lon)

        seen.add(key)
        category = categorize_tags(tags)

        pois.append(
            POI(
                name=name,
                category=category,
                latitude=lat,
                longitude=lon,
                osm_id=osm_id,
                osm_type=osm_type,
                source="overpass",
                associated_monument=associated_monument,
                distance_m=dist_m,
                tags=tags,
            )
        )

    return pois


def is_cache_fresh(cache_path: Path, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
    """Check if cache file exists and has not exceeded TTL."""
    if not cache_path.is_file():
        return False
    try:
        content = json.loads(cache_path.read_text(encoding="utf-8"))
        fetched_at_str = content.get("fetched_at")
        if not fetched_at_str:
            return False
        # Strip trailing Z if present for python fromisoformat
        clean_ts = fetched_at_str.replace("Z", "+00:00")
        fetched_at = datetime.fromisoformat(clean_ts)
        age = (datetime.now(UTC) - fetched_at).total_seconds()
        return age < ttl_seconds
    except (OSError, ValueError, KeyError) as exc:
        logger.warning("Failed to check cache freshness for %s: %s", cache_path, exc)
        return False


def save_overpass_cache(
    pois: list[POI],
    cache_path: Path = DEFAULT_CACHE_PATH,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    radius_m: int = DEFAULT_RADIUS_METERS,
    monuments_count: int = 15,
) -> None:
    """Save POIs to persistent JSON cache file."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "fetched_at": datetime.now(UTC).isoformat(),
        "ttl_seconds": ttl_seconds,
        "radius_m": radius_m,
        "monuments_count": monuments_count,
        "pois_count": len(pois),
        "pois": [p.to_dict() for p in pois],
    }
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Saved %d POIs to cache at %s", len(pois), cache_path)


def load_overpass_cache(
    cache_path: Path = DEFAULT_CACHE_PATH,
    require_fresh: bool = False,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> list[POI]:
    """Load POIs from persistent cache. Falls back to bundled cache if default not found."""
    target_path = cache_path
    if not target_path.is_file():
        if BUNDLED_CACHE_PATH.is_file():
            target_path = BUNDLED_CACHE_PATH
        else:
            raise CacheNotFoundError(
                f"Overpass POI cache not found at '{cache_path}' or bundled '{BUNDLED_CACHE_PATH}'"
            )

    try:
        data = json.loads(target_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OverpassError(f"Failed to read cache file {target_path}: {exc}") from exc

    if require_fresh:
        fetched_at_str = data.get("fetched_at", "")
        clean_ts = fetched_at_str.replace("Z", "+00:00")
        try:
            fetched_at = datetime.fromisoformat(clean_ts)
            age = (datetime.now(UTC) - fetched_at).total_seconds()
            if age >= ttl_seconds:
                raise OverpassError(f"Cache expired (age {age:.0f}s >= TTL {ttl_seconds}s)")
        except (ValueError, TypeError) as exc:
            raise OverpassError(f"Invalid timestamp in cache: {exc}") from exc

    raw_pois = data.get("pois", [])
    return [POI.from_dict(p) for p in raw_pois]


def query_overpass_api(
    lat: float,
    lon: float,
    radius_m: int = DEFAULT_RADIUS_METERS,
    endpoint: str = OVERPASS_ENDPOINT,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = 30,
) -> dict[str, Any]:
    """Execute live Overpass API query for a coordinate center."""
    query = build_overpass_query(lat, lon, radius_m)
    encoded_data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=encoded_data,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                raise OverpassError(f"Overpass API returned status {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise OverpassError(f"Overpass HTTP error: {exc.code} - {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise OverpassError(f"Overpass network error: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise OverpassError(f"Invalid JSON from Overpass API: {exc}") from exc


def fetch_pois_for_monuments(
    monuments: list[dict[str, Any]],
    cache_path: Path = DEFAULT_CACHE_PATH,
    offline: bool = False,
    force_refresh: bool = False,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    radius_m: int = DEFAULT_RADIUS_METERS,
    user_agent: str | None = None,
) -> list[POI]:
    """Retrieve POIs around monuments.

    In offline/demo mode or when cache is fresh, reads from persistent cache.
    Never executes live network requests when offline=True.
    """
    if offline or bool(os.environ.get("PLANNER_OFFLINE_MODE", "0") in ("1", "true", "True")):
        # Offline mode: must use cache
        return load_overpass_cache(cache_path=cache_path, require_fresh=False)

    if not force_refresh and is_cache_fresh(cache_path, ttl_seconds):
        logger.info("Using fresh Overpass POI cache at %s", cache_path)
        return load_overpass_cache(cache_path=cache_path, require_fresh=False)

    # Live fetch
    ua = user_agent or os.environ.get("OSM_USER_AGENT") or DEFAULT_USER_AGENT
    all_pois: list[POI] = []
    seen_keys: set[tuple[str, int]] = set()

    for m in monuments:
        slug = m["slug"]
        lat = float(m["latitude"])
        lon = float(m["longitude"])
        logger.info("Fetching Overpass POIs for '%s' (%f, %f)", slug, lat, lon)
        try:
            resp = query_overpass_api(lat, lon, radius_m=radius_m, user_agent=ua)
            pois = parse_overpass_response(
                resp,
                associated_monument=slug,
                monument_lat=lat,
                monument_lon=lon,
            )
            for p in pois:
                key = (p.osm_type, p.osm_id)
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_pois.append(p)
        except Exception as exc:
            logger.warning("Failed live fetch for '%s': %s", slug, exc)
            # If live fetch fails but existing cache exists, fall back to cache
            if cache_path.is_file() or BUNDLED_CACHE_PATH.is_file():
                logger.info("Falling back to local cache after network failure")
                return load_overpass_cache(cache_path=cache_path, require_fresh=False)
            raise OverpassError(f"Network error fetching POIs for {slug}: {exc}") from exc

    save_overpass_cache(
        all_pois,
        cache_path=cache_path,
        ttl_seconds=ttl_seconds,
        radius_m=radius_m,
        monuments_count=len(monuments),
    )
    return all_pois
