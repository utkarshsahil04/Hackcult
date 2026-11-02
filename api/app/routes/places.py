from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Query

from app.errors import AppError
from app.planner.overpass import haversine_distance, load_overpass_cache
from app.schemas import PlaceOut

logger = logging.getLogger("raahein.api.places")

router = APIRouter(prefix="/api/places", tags=["places"])


@router.get("/nearby", response_model=list[PlaceOut])
def get_nearby_places(
    monument_slug: Annotated[
        str | None,
        Query(
            description="Slug of monument to find nearby places for (e.g. 'humayuns-tomb')",
        ),
    ] = None,
    monument: Annotated[
        str | None,
        Query(
            description="Alternative alias for monument slug",
        ),
    ] = None,
    latitude: Annotated[
        float | None,
        Query(
            ge=-90.0,
            le=90.0,
            description="Center latitude (-90 to 90)",
        ),
    ] = None,
    longitude: Annotated[
        float | None,
        Query(
            ge=-180.0,
            le=180.0,
            description="Center longitude (-180 to 180)",
        ),
    ] = None,
    category: Annotated[
        str | None,
        Query(
            description="Filter by category (e.g. 'museum', 'historical', 'food', 'market', 'handicraft')",
        ),
    ] = None,
    radius_m: Annotated[
        int,
        Query(
            gt=0,
            le=100000,
            description="Search radius in meters",
        ),
    ] = 2000,
    limit: Annotated[
        int,
        Query(
            gt=0,
            le=500,
            description="Maximum number of nearby places to return",
        ),
    ] = 50,
) -> list[PlaceOut]:
    """Retrieve nearby places of interest around a monument or coordinate.

    Uses the persistent local Overpass cache from Issue #9 without live network calls.
    Returns HTTP 200 with an empty list if no places match.
    Returns HTTP 502 with UPSTREAM_PLACES_UNAVAILABLE if the cached data is unavailable.
    """
    # Validate coordinate completeness
    if (latitude is not None and longitude is None) or (latitude is None and longitude is not None):
        raise AppError(
            status_code=400,
            code="VALIDATION_ERROR",
            message="Both latitude and longitude must be provided together.",
            hint="Provide both latitude and longitude or specify monument_slug.",
        )

    # Normalize monument slug
    slug = (monument_slug or monument or "").strip()

    # Load cached Overpass data
    try:
        raw_pois = load_overpass_cache(require_fresh=False)
    except Exception as exc:
        logger.exception("Failed to load Overpass POI cache")
        raise AppError(
            status_code=502,
            code="UPSTREAM_PLACES_UNAVAILABLE",
            message="The nearby places service is currently unavailable.",
            hint="Ensure the Overpass POI cache is generated and accessible.",
        ) from exc

    results: list[PlaceOut] = []

    for poi in raw_pois:
        # Category filter
        if category and poi.category.lower() != category.strip().lower():
            continue

        # Spatial / Monument filter
        if latitude is not None and longitude is not None:
            dist = haversine_distance(latitude, longitude, poi.latitude, poi.longitude)
            if dist > radius_m:
                continue
            results.append(
                PlaceOut(
                    name=poi.name,
                    category=poi.category,
                    latitude=poi.latitude,
                    longitude=poi.longitude,
                    osm_id=poi.osm_id,
                    osm_type=poi.osm_type,
                    source=poi.source,
                    associated_monument=poi.associated_monument,
                    distance_m=round(dist, 1),
                    tags=poi.tags,
                )
            )
        elif slug:
            if poi.associated_monument.lower() != slug.lower():
                continue
            if poi.distance_m is not None and poi.distance_m > radius_m:
                continue
            results.append(
                PlaceOut(
                    name=poi.name,
                    category=poi.category,
                    latitude=poi.latitude,
                    longitude=poi.longitude,
                    osm_id=poi.osm_id,
                    osm_type=poi.osm_type,
                    source=poi.source,
                    associated_monument=poi.associated_monument,
                    distance_m=poi.distance_m,
                    tags=poi.tags,
                )
            )
        else:
            # No spatial filter: return cached POIs
            results.append(
                PlaceOut(
                    name=poi.name,
                    category=poi.category,
                    latitude=poi.latitude,
                    longitude=poi.longitude,
                    osm_id=poi.osm_id,
                    osm_type=poi.osm_type,
                    source=poi.source,
                    associated_monument=poi.associated_monument,
                    distance_m=poi.distance_m,
                    tags=poi.tags,
                )
            )

    # Sort by distance if available
    results.sort(key=lambda p: (p.distance_m is None, p.distance_m or 0.0))
    return results[:limit]
