# Raahein Offline Demo Dataset (Issue #17)

This directory contains the version-controlled demo package for running Raahein's offline demonstrations without live external dependencies.

## Artifact Policy Compliance

In accordance with repository CI policies (which reject tracked raw image binaries and generated ML artifacts in Git):
- Raw `.jpg` binaries are excluded from Git tracking via `.gitignore`.
- Neither raw binaries nor disguised base64 byte streams are committed into git repository history.
- `cached_responses.json`: Tracks canonical candidate rankings, metadata, sizes, SHA-256 checksums, and release download coordinates for all 5 demo photos.
- `demo/fetch_assets.py`: Turnkey distribution script that verifies existing local cache files and, when necessary, fetches assets from official GitHub Releases with strict SHA-256 validation.
- All recognition lookups and tour demonstrations operate 100% offline once assets are present in `demo/images/` or served via the deterministic demo cache.

## Demo Photos Specification

The 5 representative heritage photos and their immutable cryptographic checksums:

| File Name | Monument | City | Era | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `taj_mahal.jpg` | Taj Mahal | Agra | Mughal | 20,724 | `5a7f69bdbcd2a7c1193d368617769a85aaa22449b0a9c28e90ad2fb1d96db965` |
| `qutb_minar.jpg` | Qutb Minar | Delhi | Delhi Sultanate | 18,901 | `419b6920da37e72d7790bf85bf5a6286f3394be5bab21186defb84c5afafa066` |
| `humayuns_tomb.jpg` | Humayun's Tomb | Delhi | Mughal | 23,275 | `5a0a3e69c30b99e83de2e47711f24e5c2754a0f1d44851a631274746c4ecd687` |
| `red_fort.jpg` | Red Fort | Delhi | Mughal | 20,162 | `3eb1a427a85d9a17c13941a3ee5022aa33f9f7cc685e6c3863949cd3e5c58302` |
| `agra_fort.jpg` | Agra Fort | Agra | Mughal | 18,615 | `162ef044912e27449c61cfb144c6631db43c7bf5fca354a375c9e015d237b015` |

## Asset Distribution & Verification (`demo/fetch_assets.py`)

Asset downloads are managed through official immutable GitHub Releases:
- **Repository:** `utkarshsahil04/Hackcult`
- **Release Tag:** `v0.1.0-demo-assets`
- **Base URL:** `https://github.com/utkarshsahil04/Hackcult/releases/download/v0.1.0-demo-assets/`

### Verifying Local Assets
To verify existing local files without making any network requests:
```bash
python demo/fetch_assets.py --offline
```

### Fetching Missing Assets
To download missing assets from the release and verify their SHA-256 checksums:
```bash
python demo/fetch_assets.py
```

### Fresh-Checkout State & Release Status
Until repository maintainers create and publish the GitHub release tag `v0.1.0-demo-assets`, attempts to download on a fresh checkout without local files will report:
```text
[RELEASE_PENDING] Asset download returned HTTP 404 (GitHub Release 'v0.1.0-demo-assets' has not yet been published by maintainer).
```
Fresh-checkout downloads are reported honestly as pending and will never claim to be verified until the remote assets are actually published and checksum-validated.

---

## Maintainer Runbook: Publishing Release Assets

Repository maintainers must perform this one-time step to publish the 5 demo assets to GitHub Releases:

### Using GitHub CLI (`gh`)
```bash
# 1. Verify local image files exist and pass SHA-256 checks
python demo/fetch_assets.py --offline

# 2. Publish release and upload the 5 JPEG assets
gh release create v0.1.0-demo-assets \
  demo/images/taj_mahal.jpg \
  demo/images/qutb_minar.jpg \
  demo/images/humayuns_tomb.jpg \
  demo/images/red_fort.jpg \
  demo/images/agra_fort.jpg \
  --title "v0.1.0 Demo Assets" \
  --notes "Official deterministic demo photos for Raahein offline demonstrations (Issue #17)."
```

### Using GitHub Web UI
1. Navigate to: `https://github.com/utkarshsahil04/Hackcult/releases/new`
2. Set **Tag version** to: `v0.1.0-demo-assets`
3. Set **Release title** to: `v0.1.0 Demo Assets`
4. Attach the 5 JPEG images from `demo/images/`:
   - `taj_mahal.jpg`
   - `qutb_minar.jpg`
   - `humayuns_tomb.jpg`
   - `red_fort.jpg`
   - `agra_fort.jpg`
5. Click **Publish release**.

---

## Running the Automated Demo Walkthrough

To run the full 2-minute live presentation:
```bash
python demo/run_demo.py
```

To run rapid automated verification (< 2 seconds):
```bash
python demo/run_demo.py --fast
```

To point against a running external FastAPI backend:
```bash
python demo/run_demo.py --url http://127.0.0.1:8000
```
