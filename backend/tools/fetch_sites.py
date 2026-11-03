"""Resolve curated Delhi-NCR heritage site names to real OpenStreetMap coordinates (Nominatim).

Writes backend/app/db/seed_data/sites.json. Re-run to refresh; sites that cannot be resolved are
reported and skipped, never guessed. Nominatim policy: identify the app, max 1 request/second.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "app" / "db" / "seed_data" / "sites.json"
UA = "raahein-heritage-planner/0.1 (hackathon; contact via repo)"
# (slug, display name, Nominatim query, era label, style label)
SITES = [
    ("india-gate", "India Gate", "India Gate, New Delhi", "20th century (memorial, 1931)", "War memorial (Lutyens)"),
    ("lotus-temple", "Lotus Temple", "Lotus Temple", "20th century (1986)", "Expressionist / Bahá'í House of Worship"),
    ("hauz-khas-complex", "Hauz Khas Complex", "Hauz Khas Fort", "Delhi Sultanate (14th century)", "Tughlaq-era tank, madrasa and tombs"),
    ("agrasen-ki-baoli", "Agrasen ki Baoli", "Agrasen ki Baoli", "Medieval stepwell", "Stepwell (baoli)"),
    ("feroz-shah-kotla", "Feroz Shah Kotla", "Feroz Shah Kotla, Delhi", "Delhi Sultanate (14th century)", "Tughlaq fortified palace complex"),
    ("rashtrapati-bhavan", "Rashtrapati Bhavan", "Rashtrapati Bhavan, New Delhi", "20th century (1929)", "Lutyens' Delhi / Indo-colonial"),
    ("sunder-nursery", "Sunder Nursery", "Sunder Nursery", "Mughal era garden precinct", "Mughal garden and tombs"),
    ("abdul-rahim-khan-i-khana-tomb", "Tomb of Abdul Rahim Khan-i-Khana", "Khan-i-Khana tomb", "Mughal (17th century)", "Mughal tomb"),
    ("khirki-masjid", "Khirki Masjid", "Khirki Masjid, Delhi", "Delhi Sultanate (14th century)", "Tughlaq-era mosque"),
    ("sultan-ghari", "Sultan Ghari", "Sultan Ghari", "Delhi Sultanate (13th century)", "Early Islamic tomb"),
    ("nizamuddin-dargah", "Hazrat Nizamuddin Dargah", "Nizamuddin Dargah", "Delhi Sultanate (14th century)", "Sufi shrine"),
    ("raj-ghat", "Raj Ghat", "Raj Ghat", "20th century (1948)", "Memorial"),
    ("akshardham-delhi", "Akshardham Temple, Delhi", "Akshardham", "21st century (2005)", "Neo-traditional Hindu temple"),
    ("fatehpuri-masjid", "Fatehpuri Masjid", "Fatehpuri Masjid", "Mughal (1650)", "Mughal mosque"),
]


def lookup(query: str) -> dict | None:
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "in", "viewbox": "76.9,28.95,77.6,28.2", "bounded": 1}
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        hits = json.loads(r.read())
    return hits[0] if hits else None


def main() -> int:
    sites, missing = [], []
    for slug, name, query, era, style in SITES:
        hit = lookup(query)
        time.sleep(1.2)
        if not hit:
            missing.append(slug)
            continue
        lat, lon = round(float(hit["lat"]), 5), round(float(hit["lon"]), 5)
        if not (28.2 <= lat <= 28.95 and 76.9 <= lon <= 77.6):  # must fall in Delhi NCR
            missing.append(f"{slug} (resolved outside Delhi NCR: {lat},{lon})")
            continue
        sites.append({
            "slug": slug, "name": name, "latitude": lat, "longitude": lon,
            "osm_type": hit["osm_type"], "osm_id": hit["osm_id"], "era": era,
            "architectural_style": style, "location": hit["display_name"].split(", Delhi")[0][:120],
            "city": "Delhi",
        })
        print("ok", slug, lat, lon, hit["osm_type"], hit["osm_id"])
    OUT.write_text(json.dumps(sites, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(sites)} sites; unresolved: {missing or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
