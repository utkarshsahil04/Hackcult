"""Asset fetcher and integrity verifier for Raahein demo photos (Issue #17).

Provides reproducible asset retrieval from official GitHub Release distribution
with strict SHA-256 verification and local-cache-first offline support.

Usage:
    python demo/fetch_assets.py                    # Verify local cache or fetch from release
    python demo/fetch_assets.py --offline          # Offline verification only (no network calls)
    python demo/fetch_assets.py --dest custom/dir  # Store assets in custom directory
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("raahein.demo.fetch_assets")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_FILE = REPO_ROOT / "demo" / "cached_responses.json"
DEFAULT_IMAGES_DIR = REPO_ROOT / "demo" / "images"

# Expected asset release tag
EXPECTED_RELEASE_TAG = "v0.1.0-demo-assets"


@dataclass
class AssetResult:
    """Outcome of verifying or fetching a single asset."""

    filename: str
    status: str
    path: Path | None
    expected_sha: str
    actual_sha: str | None
    size_bytes: int
    message: str


def compute_file_sha256(path: Path) -> str:
    """Compute lowercase SHA-256 hexadecimal digest for a file."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def verify_file_sha256(path: Path, expected_sha: str) -> bool:
    """Return True if path exists and its SHA-256 digest matches expected_sha."""
    if not path.is_file():
        return False
    return compute_file_sha256(path) == expected_sha.lower()


def fetch_single_asset(
    photo: dict[str, Any],
    dest_dir: Path,
    force: bool = False,
    offline: bool = False,
    timeout: float = 15.0,
) -> AssetResult:
    """Verify or download a single demo asset with SHA-256 verification.

    Status codes:
        - "verified_local": Asset exists locally and passed SHA-256 verification.
        - "downloaded_and_verified": Asset was downloaded and passed SHA-256.
        - "release_pending": Download returned 404 (release not yet published on GitHub).
        - "missing_offline": Asset missing locally and offline mode prevented download.
        - "checksum_mismatch": Asset bytes did not match expected SHA-256 digest.
        - "network_error": Download failed due to network / connection error.
    """
    filename = photo.get("filename", "")
    expected_sha = str(photo.get("sha256", "")).lower()
    size_bytes = int(photo.get("size_bytes", 0))
    target_path = dest_dir / filename

    source = photo.get("source", {})
    download_url = source.get("download_url") or ""
    release_tag = source.get("release_tag", EXPECTED_RELEASE_TAG)

    # 1. Local Cache Check
    if target_path.is_file():
        actual_sha = compute_file_sha256(target_path)
        if actual_sha == expected_sha:
            if not force:
                return AssetResult(
                    filename=filename,
                    status="verified_local",
                    path=target_path,
                    expected_sha=expected_sha,
                    actual_sha=actual_sha,
                    size_bytes=size_bytes,
                    message="Cached locally and verified against SHA-256",
                )
        else:
            # Local file is corrupted
            if offline:
                return AssetResult(
                    filename=filename,
                    status="checksum_mismatch",
                    path=target_path,
                    expected_sha=expected_sha,
                    actual_sha=actual_sha,
                    size_bytes=size_bytes,
                    message=f"Local file corrupted: expected {expected_sha[:8]}..., got {actual_sha[:8]}...",
                )
            # Remove corrupt local file before attempting re-download
            try:
                target_path.unlink()
            except OSError:
                pass

    # 2. Offline Mode Guard
    if offline:
        return AssetResult(
            filename=filename,
            status="missing_offline",
            path=None,
            expected_sha=expected_sha,
            actual_sha=None,
            size_bytes=size_bytes,
            message="Asset missing from local cache (offline mode active)",
        )

    # 3. Download from GitHub Release
    if not download_url:
        return AssetResult(
            filename=filename,
            status="missing_offline",
            path=None,
            expected_sha=expected_sha,
            actual_sha=None,
            size_bytes=size_bytes,
            message="No download URL configured in cached_responses.json",
        )

    dest_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": "Raahein-Demo-AssetFetcher/1.0"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            downloaded_bytes = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return AssetResult(
                filename=filename,
                status="release_pending",
                path=None,
                expected_sha=expected_sha,
                actual_sha=None,
                size_bytes=size_bytes,
                message=(
                    f"Asset download returned HTTP 404. GitHub Release '{release_tag}' "
                    "has not yet been published by maintainer. See demo/README.md for publication instructions."
                ),
            )
        return AssetResult(
            filename=filename,
            status="network_error",
            path=None,
            expected_sha=expected_sha,
            actual_sha=None,
            size_bytes=size_bytes,
            message=f"HTTP download error: {exc.code} {exc.reason}",
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return AssetResult(
            filename=filename,
            status="network_error",
            path=None,
            expected_sha=expected_sha,
            actual_sha=None,
            size_bytes=size_bytes,
            message=f"Network download error: {exc}",
        )

    # 4. Verify Downloaded Bytes SHA-256
    downloaded_sha = hashlib.sha256(downloaded_bytes).hexdigest().lower()
    if downloaded_sha != expected_sha:
        return AssetResult(
            filename=filename,
            status="checksum_mismatch",
            path=None,
            expected_sha=expected_sha,
            actual_sha=downloaded_sha,
            size_bytes=len(downloaded_bytes),
            message=f"Downloaded bytes failed SHA-256 verification: expected {expected_sha[:8]}..., got {downloaded_sha[:8]}...",
        )

    # 5. Atomic File Write
    try:
        with tempfile.NamedTemporaryFile(dir=dest_dir, delete=False) as tf:
            tf.write(downloaded_bytes)
            tmp_name = tf.name
        Path(tmp_name).replace(target_path)
    except OSError as exc:
        return AssetResult(
            filename=filename,
            status="network_error",
            path=None,
            expected_sha=expected_sha,
            actual_sha=downloaded_sha,
            size_bytes=len(downloaded_bytes),
            message=f"Failed to write asset to disk: {exc}",
        )

    return AssetResult(
        filename=filename,
        status="downloaded_and_verified",
        path=target_path,
        expected_sha=expected_sha,
        actual_sha=downloaded_sha,
        size_bytes=len(downloaded_bytes),
        message="Downloaded and successfully verified against SHA-256",
    )


def fetch_all_assets(
    cache_file: Path | None = None,
    dest_dir: Path | None = None,
    force: bool = False,
    offline: bool = False,
    timeout: float = 15.0,
) -> dict[str, AssetResult]:
    """Fetch and verify all demo photos listed in cached_responses.json."""
    cache_path = cache_file or DEFAULT_CACHE_FILE
    env_dir = os.environ.get("RAAHEIN_DEMO_IMAGES_DIR") or os.environ.get("RAAHEIN_DEMO_ASSET_DIR")
    target_dir = dest_dir or (Path(env_dir) if env_dir else DEFAULT_IMAGES_DIR)

    if not cache_path.is_file():
        raise FileNotFoundError(f"Cache file not found at {cache_path}")

    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    photos = raw.get("photos", [])

    results: dict[str, AssetResult] = {}
    for p in photos:
        fn = p.get("filename", "")
        if fn:
            results[fn] = fetch_single_asset(
                photo=p,
                dest_dir=target_dir,
                force=force,
                offline=offline,
                timeout=timeout,
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and verify Raahein demo assets.")
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Destination directory for demo images (default: demo/images)",
    )
    parser.add_argument(
        "--cache-file",
        type=Path,
        default=None,
        help="Path to cached_responses.json",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Operate in offline mode; only verify existing local files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if files exist locally",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed logging",
    )
    args = parser.parse_args()

    results = fetch_all_assets(
        cache_file=args.cache_file,
        dest_dir=args.dest,
        force=args.force,
        offline=args.offline,
    )

    all_verified = True
    any_pending = False
    any_failed = False

    print("\n" + "=" * 70)
    print("  RAAHEIN DEMO ASSET INTEGRITY REPORT")
    print("=" * 70)

    for fn, res in results.items():
        tag = f"[{res.status.upper()}]"
        print(f"  {tag:<26} {fn:<18} ({res.size_bytes:,} bytes)")
        if not args.quiet:
            print(f"    Expected SHA: {res.expected_sha}")
            if res.actual_sha:
                print(f"    Actual SHA:   {res.actual_sha}")
            print(f"    Details:      {res.message}")

        if res.status in ("verified_local", "downloaded_and_verified"):
            pass
        elif res.status == "release_pending":
            all_verified = False
            any_pending = True
        else:
            all_verified = False
            any_failed = True

    print("=" * 70)
    if all_verified:
        print("  Summary: All 5 demo assets verified and ready for offline use.\n")
        return 0
    elif any_pending and not any_failed:
        print("  Summary: Assets are pending GitHub Release publication by maintainer.")
        print("  Refer to demo/README.md for release creation instructions.\n")
        return 2
    else:
        print("  Summary: One or more demo assets failed verification or are missing.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
