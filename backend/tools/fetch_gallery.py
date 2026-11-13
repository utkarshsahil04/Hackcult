"""Download a licensed reference-photo gallery from Wikimedia Commons into commons-gallery/<slug>/<n>.jpg.

Writes commons-gallery/credits.json. Resumable: files already on disk are kept, titles in .rejected.txt
(one per line, add a title there when you delete a bad photo) and in eval-commons/manifest.json are never fetched.
Usage: py tools/fetch_gallery.py [--probe]   (--probe only counts candidates per category)
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "commons-gallery"
CREDITS = OUT / "credits.json"
REJECTED = OUT / ".rejected.txt"
EVAL = ROOT / "eval-commons" / "manifest.json"
API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "heritage-gallery-fetch/1.0"}
WIDTH, MIN_WIDTH, TARGET, MINIMUM, PER_AUTHOR, DEPTH = 800, 800, 70, 40, 8, 2
FREE = re.compile(r"^(cc0|public domain|pd[ -]|cc[ -]by(-sa)?[ -]\d)", re.IGNORECASE)
BAD = re.compile(
    r"\b(plan|map|drawing|painting|engraving|litho\w*|sketch|illustration|logo|coin|stamp|portrait|aerial|satellite|"
    r"drone|museum|manuscript|poster|flag|emblem|diagram|model|miniature|postcard|1[0-8]\d\d|panorama of|"
    r"statue|bust|costume|dance|festival|people|crowd|parade|speech|ceremony|visit|meeting|minister|president|"
    r"fireworks|painted|print|artwork|signage|plaque|inscription|book|cover)\b",
    re.IGNORECASE,
)
CATEGORIES = {
    "red-fort": ["Red Fort (Delhi)", "Red Fort"],
    "agra-fort": ["Agra Fort"],
    "akbars-tomb": ["Akbar's Tomb", "Tomb of Akbar the Great"],
    "itimad-ud-daulah": ["Tomb of I'timād-ud-Daulah", "Tomb of Itimad-Ud-Daulah"],
    "jama-masjid": ["Jama Masjid, Delhi"],
    "safdarjungs-tomb": ["Safdarjung's Tomb"],
    "purana-qila": ["Purana Qila"],
    "tughlaqabad-fort": ["Tughlaqabad Fort"],
    "jantar-mantar": ["Jantar Mantar, New Delhi"],
    "lodhi-gardens": ["Lodi Gardens"],
    "hauz-khas-complex": ["Hauz Khas Complex"],
    "agrasen-ki-baoli": ["Agrasen ki Baoli"],
    "feroz-shah-kotla": ["Feroz Shah Kotla"],
    "rashtrapati-bhavan": ["Rashtrapati Bhavan"],
    "sunder-nursery": ["Sunder Nursery"],
    "abdul-rahim-khan-i-khana-tomb": ["Tomb of Abdul Rahim Khan-I-Khana"],
    "khirki-masjid": ["Khirki Mosque"],
    "nizamuddin-dargah": ["Nizamuddin Dargah"],
    "raj-ghat": ["Raj Ghat"],
    "akshardham-delhi": ["Akshardham (Delhi)"],
    "fatehpuri-masjid": ["Fatehpuri Mosque"],
}

_last = 0.0


def fetch(url: str) -> bytes:
    """GET with <=1 request/s and exponential backoff (10 s, x2, 5 retries) on 429/5xx."""
    global _last
    delay = 10
    for attempt in range(6):
        time.sleep(max(0.0, 1.0 - (time.time() - _last)))
        _last = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if (exc.code != 429 and exc.code < 500) or attempt == 5:
                raise
            delay = max(delay, int(exc.headers.get("Retry-After") or 0) + 1)
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 5:
                raise
        print(f"  backoff {delay}s", flush=True)
        time.sleep(delay)
        delay *= 2
    raise RuntimeError("unreachable")


def get(**params: str) -> dict:
    query = urllib.parse.urlencode({"format": "json", "formatversion": "2", **params})
    return json.loads(fetch(f"{API}?{query}"))


def members(category: str, kind: str) -> list[str]:
    out, cont = [], {}
    while True:
        data = get(action="query", list="categorymembers", cmtitle=f"Category:{category}", cmtype=kind, cmlimit="500", **cont)
        out += [m["title"] for m in data["query"]["categorymembers"]]
        if "continue" not in data:
            return out
        cont = {"cmcontinue": data["continue"]["cmcontinue"]}


def candidate_titles(slug: str) -> list[str]:
    files, seen = [], set()
    for top in CATEGORIES[slug]:
        if get(action="query", titles=f"Category:{top}")["query"]["pages"][0].get("missing"):
            print(f"  MISSING category {top!r}", flush=True)
            continue
        level = [top]
        for depth in range(DEPTH + 1):
            nxt = []
            for cat in level:
                if cat in seen:
                    continue
                seen.add(cat)
                files += members(cat, "file")
                if depth < DEPTH:
                    nxt += [c.removeprefix("Category:") for c in members(cat, "subcat") if not BAD.search(c)]
            level = nxt
            if len(files) > 2500:
                break
    return list(dict.fromkeys(files))


def clean(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"https?://\S+", "", re.sub(r"<[^>]+>", " ", text))).split())


def usable(titles: list[str]) -> list[dict]:
    """Imageinfo for titles, keeping only wide JPEG photos with a free licence."""
    out = []
    for i in range(0, len(titles), 50):
        pages = get(action="query", prop="imageinfo", iiprop="url|extmetadata|size|mime|mediatype", iiurlwidth=str(WIDTH),
                    titles="|".join(titles[i:i + 50]))["query"]["pages"]
        for page in pages:
            info = (page.get("imageinfo") or [None])[0]
            if not info or info["mime"] != "image/jpeg" or info["mediatype"] != "BITMAP" or info["width"] < MIN_WIDTH:
                continue
            if info["width"] > 3 * info["height"] or "thumburl" not in info:
                continue
            meta = info["extmetadata"]
            licence = meta.get("LicenseShortName", {}).get("value", "")
            if not FREE.match(licence):
                continue
            out.append({
                "commons_title": page["title"],
                "page_url": info["descriptionurl"],
                "thumb": info["thumburl"],
                "author": clean(meta.get("Artist", {}).get("value", ""))[:80] or "Unknown",
                "license": licence,
                "license_url": meta.get("LicenseUrl", {}).get("value", ""),
            })
    return out


def pick(cands: list[dict], cap: int | None) -> list[dict]:
    """Order candidates round-robin across authors so bursts from one uploader do not crowd out the rest."""
    by_author: dict[str, list[dict]] = {}
    for c in cands:
        by_author.setdefault(c["author"].lower(), []).append(c)
    queues = [q[:cap] if cap else q for q in by_author.values()]
    return [q[i] for i in range(max(map(len, queues), default=0)) for q in queues if i < len(q)]


def main() -> None:
    probe = "--probe" in sys.argv
    OUT.mkdir(exist_ok=True)
    credits = json.loads(CREDITS.read_text(encoding="utf-8")) if CREDITS.exists() else []
    credits = [c for c in credits if (OUT / c["file"]).exists()]
    skip = {t.strip() for t in REJECTED.read_text(encoding="utf-8").splitlines()} if REJECTED.exists() else set()
    eval_titles = {m["title"] for m in json.loads(EVAL.read_text(encoding="utf-8"))}
    skip |= eval_titles
    taken = {c["commons_title"] for c in credits}
    print(f"eval titles excluded up front: {len(eval_titles)}", flush=True)
    for slug in CATEGORIES:
        mine = [c for c in credits if c["slug"] == slug]
        titles = [t for t in candidate_titles(slug) if t.startswith("File:") and not BAD.search(t)]
        hit = [t for t in titles if t in eval_titles]
        titles = [t for t in titles if t not in skip and t not in taken]
        print(f"{slug}: {len(titles)} titles to check, {len(mine)} on disk, eval-skipped {len(hit)}", flush=True)
        if probe or len(mine) >= TARGET:
            continue
        cands = usable(titles)
        order = pick(cands, PER_AUTHOR)
        if len(mine) + len(order) < MINIMUM:
            order = pick(cands, None)  # not enough distinct authors: relax the cap
        n = max([int(Path(c["file"]).stem) for c in mine], default=0)
        (OUT / slug).mkdir(exist_ok=True)
        for c in order:
            if len(mine) >= TARGET:
                break
            try:
                data = fetch(c["thumb"])
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                print(f"  skip {c['commons_title']}: {exc}", flush=True)
                continue
            if data[:2] != b"\xff\xd8":
                continue
            n += 1
            (OUT / slug / f"{n}.jpg").write_bytes(data)
            entry = {"slug": slug, "file": f"{slug}/{n}.jpg", **{k: c[k] for k in ("commons_title", "page_url", "author", "license", "license_url")}}
            mine.append(entry)
            credits.append(entry)
            taken.add(c["commons_title"])
        CREDITS.write_text(json.dumps(credits, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"  {slug}: {len(mine)} photos, {len({c['author'] for c in mine})} authors", flush=True)
    if probe:
        return
    # rewrite credits from what exists, then self-check
    credits = [c for c in credits if (OUT / c["file"]).exists()]
    CREDITS.write_text(json.dumps(credits, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    on_disk = {p.relative_to(OUT).as_posix() for p in OUT.glob("*/*.jpg")}
    assert on_disk == {c["file"] for c in credits}, "credits.json and files on disk disagree"
    assert all(FREE.match(c["license"]) for c in credits), "non-free licence in credits.json"
    print("self-check ok;", Counter(c["slug"] for c in credits))


if __name__ == "__main__":
    main()
