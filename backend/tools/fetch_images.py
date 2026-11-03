"""Write frontend/lib/images.json: one freely licensed Wikimedia Commons photo per monument, with its credit.

CI rejects tracked raster images, so the UI loads these from Commons. Refuses to write unless every
monument has a free licence. Usage: python tools/fetch_images.py
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend" / "lib" / "images.json"
API = "https://commons.wikimedia.org/w/api.php"
WIKI = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "raahein-image-tool/0.1 (https://github.com/utkarshsahil04/Hackcult)"}
WIDTH = 1280
FREE = re.compile(r"^(cc[ -]?by|cc0|public domain|pd\b)", re.I)

# Wikipedia article whose lead image is used, or "File:..." where a specific Commons photo was chosen by eye.
SITES = {
    "taj-mahal": "Taj Mahal",
    "agra-fort": "File:20191204 Czerwony Fort w Agrze 0936 6599.jpg",
    "red-fort": "Red Fort",
    "humayuns-tomb": "File:20191205 Grobowiec Humajuna w Delhi 1055 6794.jpg",
    "qutb-complex": "Qutb Minar",
    "fatehpur-sikri": "Fatehpur Sikri",
    "akbars-tomb": "File:Akbar's Tomb - Agra - Uttar Pradesh - 001.jpg",
    "itimad-ud-daulah": "File:Itimad-ud-Daulah Agra 04.jpg",
    "jama-masjid": "Jama Masjid, Delhi",
    "safdarjungs-tomb": "Safdarjung's Tomb",
    "purana-qila": "Purana Qila",
    "tughlaqabad-fort": "File:Tughlaqabad fort wall.jpg",
    "jantar-mantar": "Jantar Mantar, New Delhi",
    "mehrauli-archaeological-park": "Mehrauli Archaeological Park",
    "lodhi-gardens": "Lodi Gardens",
    "india-gate": "India Gate",
    "lotus-temple": "Lotus Temple",
    "hauz-khas-complex": "Hauz Khas Complex",
    "agrasen-ki-baoli": "Agrasen ki Baoli",
    "feroz-shah-kotla": "Feroz Shah Kotla",
    "rashtrapati-bhavan": "Rashtrapati Bhavan",
    "sunder-nursery": "Sunder Nursery",
    "abdul-rahim-khan-i-khana-tomb": "File:Tomb of Abdul Rahim Khan-I-Khana, Delhi.jpg",
    "khirki-masjid": "Khirki Masjid",
    "nizamuddin-dargah": "Nizamuddin Dargah",
    "raj-ghat": "Raj Ghat and associated memorials",
    "akshardham-delhi": "Swaminarayan Akshardham (Delhi)",
    "fatehpuri-masjid": "Fatehpuri Masjid",
}


def get(url: str, **params: str) -> dict:
    query = urllib.parse.urlencode({"format": "json", "formatversion": "2", **params})
    request = urllib.request.Request(f"{url}?{query}", headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def lead_file(title: str) -> str:
    page = get(WIKI, action="query", prop="pageimages", piprop="name", redirects="1", titles=title)["query"]["pages"][0]
    if "pageimage" not in page:
        raise LookupError(f"no lead image on the article {title!r}")
    return "File:" + page["pageimage"]


def strip_tags(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text)).split())


def image_record(file: str) -> dict:
    page = get(API, action="query", prop="imageinfo", iiprop="url|extmetadata|size", iiurlwidth=str(WIDTH), titles=file)["query"]["pages"][0]
    if "imageinfo" not in page:
        raise LookupError(f"{file} is not on Commons")
    info = page["imageinfo"][0]
    meta = info["extmetadata"]
    licence = meta.get("LicenseShortName", {}).get("value", "")
    if not FREE.match(licence):
        raise ValueError(f"{file} has a non-free licence: {licence!r}")
    return {
        "url": info["thumburl"].split("?")[0],  # the query string is only tracking
        "page": info["descriptionurl"],
        "artist": re.sub(r"https?://\S+", "", strip_tags(meta.get("Artist", {}).get("value", "")))[:80].strip() or "Commons contributor",
        "licence": licence,
    }


def main() -> None:
    records, problems = {}, []
    for slug, site in SITES.items():
        try:
            file = site if site.startswith("File:") else lead_file(site)
            records[slug] = image_record(file)
            print(f"{slug}: {records[slug]['licence']} | {file}")
        except (LookupError, ValueError, OSError) as exc:
            problems.append(f"{slug}: {exc}")
        time.sleep(0.2)
    if problems:
        sys.exit("not writing images.json:\n" + "\n".join(problems))
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} images to {OUT}")


if __name__ == "__main__":
    main()
