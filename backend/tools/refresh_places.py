"""Replace the bundled nearby-places cache with live OpenStreetMap data for every monument in the DB.

Refuses to overwrite the cache unless every region was fetched: a partial refresh would silently
hide places. Usage: python tools/refresh_places.py
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.planner.matrix import read_monuments_from_db  # noqa: E402
from app.planner.overpass import (  # noqa: E402
    DEFAULT_RADIUS_METERS,
    DEFAULT_USER_AGENT,
    build_overpass_query,
    parse_overpass_response,
    save_overpass_cache,
)

BUNDLED = Path(__file__).resolve().parents[1] / "app" / "planner" / "data" / "overpass_pois.json"
# One query per region instead of one per monument: the public servers reject the repeated load.
REGIONS = {"delhi": "28.40,77.05,28.75,77.35", "agra": "27.05,77.60,27.26,78.08"}
ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)


def fetch_region(bbox: str) -> dict:
    query = build_overpass_query(0, 0, 1).replace("(around:1,0,0)", f"({bbox})")
    query = re.sub(r"\[timeout:\d+\]", "[timeout:170]", query)
    data = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(6):
        endpoint = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            req = urllib.request.Request(endpoint, data=data, headers={"User-Agent": DEFAULT_USER_AGENT})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except Exception as exc:  # public servers: try the next one, report if none recover
            print(f"retry {endpoint}: {exc}")
            time.sleep(15)
    sys.exit(f"not overwriting cache; region {bbox} failed")


responses = [fetch_region(bbox) for bbox in REGIONS.values()]
print("elements", [len(r.get("elements", [])) for r in responses])
monuments = read_monuments_from_db()
pois, seen = [], set()
for m in monuments:
    lat, lon = float(m["latitude"]), float(m["longitude"])
    for resp in responses:
        for p in parse_overpass_response(resp, associated_monument=m["slug"], monument_lat=lat, monument_lon=lon):
            if p.distance_m is not None and p.distance_m <= DEFAULT_RADIUS_METERS and (p.osm_type, p.osm_id) not in seen:
                seen.add((p.osm_type, p.osm_id))
                pois.append(p)
if not pois:
    sys.exit("not overwriting cache; no places found")
save_overpass_cache(pois, cache_path=BUNDLED, radius_m=DEFAULT_RADIUS_METERS, monuments_count=len(monuments))
print(f"wrote {len(pois)} real places to {BUNDLED}")
