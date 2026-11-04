"""The shape of a planned route on the map: real roads from OSRM, or straight lines if that is unavailable.

A plan is already valid without this, so a routing failure must never fail the request.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from functools import lru_cache
from itertools import pairwise
from typing import Any

logger = logging.getLogger("raahein.planner.route_line")

ROUTE_ENDPOINTS = {
    "driving-car": "https://routing.openstreetmap.de/routed-car/route/v1/driving",
    "foot-walking": "https://routing.openstreetmap.de/routed-foot/route/v1/foot",
}
TIMEOUT_SECONDS = 6

Point = tuple[float, float]  # latitude, longitude


class RouteLineUnavailable(Exception):
    pass


def _download(profile: str, points: tuple[Point, ...]) -> dict[str, Any]:
    coords = ";".join(f"{lng},{lat}" for lat, lng in points)
    request = urllib.request.Request(
        f"{ROUTE_ENDPOINTS[profile]}/{coords}?overview=false&steps=true&geometries=geojson",
        headers={"User-Agent": "raahein-heritage-planner/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError) as exc:  # network failures, timeouts, or a non-JSON error page
        raise RouteLineUnavailable(str(exc)) from exc
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RouteLineUnavailable(f"OSRM returned {data.get('code')}")
    return data


@lru_cache(maxsize=512)  # only successes are cached: exceptions are not, so a brief outage can recover
def _road_legs(profile: str, points: tuple[Point, ...]) -> tuple[tuple[Point, ...], ...]:
    legs = _download(profile, points)["routes"][0]["legs"]
    if len(legs) != len(points) - 1:
        raise RouteLineUnavailable("OSRM returned the wrong number of legs")
    road_legs = []
    for leg in legs:
        line: list[Point] = []
        for step in leg["steps"]:
            for lng, lat in step["geometry"]["coordinates"]:
                point = (round(lat, 5), round(lng, 5))
                if not line or line[-1] != point:
                    line.append(point)
        road_legs.append(tuple(line))
    return tuple(road_legs)


def route_line(profile: str, points: list[Point]) -> dict[str, Any]:
    """One line per leg between consecutive points. `source` says whether they follow real roads."""
    try:
        legs = _road_legs(profile, tuple(points))
        return {"source": "roads", "legs": [[list(p) for p in leg] for leg in legs]}
    except (RouteLineUnavailable, KeyError, IndexError, TypeError) as exc:
        logger.warning("Using straight route lines: %s", exc)
        return {"source": "straight", "legs": [[list(a), list(b)] for a, b in pairwise(points)]}
