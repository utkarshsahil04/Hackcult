# Raahein

> Photograph a monument. Discover its story, explore it in 3D, and follow the
> historical threads that connect it to places across India.

Built for **HackCult '26** (Track: Culture & Digital Heritage). Launch region: the Golden Triangle (Delhi, Agra, Jaipur).

## Features

1. AI monument recognition from a photo
2. Interactive 3D visualisation with clickable hotspots
3. Nearby cultural discovery (sites, museums, food, markets, handicrafts)
4. Historical connections across dynasties, rulers, events and styles
5. AI-powered tour planner (solver-based, constraint-checked)
6. Story-based historical journey (chapters, narration, timeline)

## Tech stack (hackathon)

| Part | Tools |
|---|---|
| Frontend | Next.js PWA on Vercel |
| Backend | FastAPI on a GPU laptop, exposed with a Cloudflare tunnel |
| Recognition | SigLIP, DINOv2 and CLIP embeddings with FAISS |
| Stories | Gemini Flash-Lite, pre-generated and cached |
| Data | SQLite seed |
| Maps and tours | OpenStreetMap, Overpass, OpenRouteService, OR-Tools |

After the hackathon we move to AWS (Lambda, DynamoDB, Amplify, S3, CloudFront).

## Project layout

```
api/        FastAPI HTTP application
backend/    SQLite heritage data and tour-planner package
ml/         Standalone recognition package, manifests, config and fast tests
.github/    CI workflow and CODEOWNERS
data/       Ignored raw images, caches and generated recognition artifacts
```

There is currently no `frontend/` directory. CI runs backend checks, conditional frontend checks,
and isolated ML lint/unit tests that do not download checkpoints or require CUDA.

## Setup

```powershell
git clone https://github.com/utkarshsahil04/Hackcult.git
cd Hackcult
copy .env.example .env        # fill in your keys; .env is never committed
pip install pre-commit
pre-commit install            # blocks commits that contain secrets
```

Test the secret check anytime with `pre-commit run --all-files`.

## Database (SQLite seed)

Read-only heritage data lives in a SQLite file built from JSON in `backend/app/db/seed_data/`.

```powershell
cd backend
pip install -r requirements.txt
python -m app.db.seed            # create / refresh backend/data/raahein.db (safe to re-run)
python -m app.db.seed --check    # validate the data files only
python -m pytest                 # schema + seed tests
```

Set `SQLITE_DB_PATH` in `.env` to change the location. Every historical claim needs two sources
from different publishers; legends are flagged `is_legend`. See `backend/app/db/seed_data/README.md`.

## Monument recognition

The standalone `raahein_ml` package reads the 15 canonical slugs directly from
`backend/app/db/seed_data/monuments.json`. It never imports either existing top-level `app`
package. Raw images, embedding caches and finalized FAISS artifacts live under ignored `data/`;
only provenance, manifests, configuration and honest evaluation results are tracked.

### WSL2 GPU setup

Production recognition requires WSL2 Ubuntu, an NVIDIA driver with CUDA support, and Python 3.12.
FAISS remains on CPU. CPU encoder execution is available only through an explicit development
override and is never selected automatically.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1
python -m pip install -e './ml[gpu,test]'
export HF_HOME="$PWD/data/cache/huggingface"
python -m raahein_ml fetch-models
```

For CPU-only development commands, set both `RAAHEIN_ML_DEVICE=cpu` and
`RAAHEIN_ML_ALLOW_CPU=true`. Final artifacts must be built and served with their recorded device,
precision and preprocessing configuration.

### Curation and artifacts

The supplied external train/test folders are not trusted inputs: their licences are unknown and
their splits contain leakage. Populate `ml/catalog/sources.csv` only with independently verified
public-domain, CC0, CC BY or CC BY-SA sources, then run the pipeline in order:

```bash
python -m raahein_ml.manifest fetch
python -m raahein_ml.manifest scan
# Resolve every row in ml/manifests/duplicate_review.csv.
python -m raahein_ml.manifest build
python -m raahein_ml build
python -m raahein_ml calibrate
python -m raahein_ml validate --artifact data/artifacts/<artifact-id>
python -m raahein_ml smoke --artifact data/artifacts/<artifact-id>
python -m raahein_ml evaluate --artifact data/artifacts/<artifact-id> --update-readme
```

`manifest scan` writes ignored local drafts under `data/cache/` and refreshes only the tracked
manual-review queue. It cannot overwrite a previously validated tracked manifest; only a successful
`manifest build` replaces final manifest files.

`manifest build` refuses missing provenance, pending near-duplicate reviews, cross-label or
cross-collection duplicates, infeasible per-class quotas, and any cross-split leakage. Calibration
uses its own 50 OOD images and freezes model thresholds, the fusion margin, active strategy and all
final-set hashes before evaluation. The evaluation command requires a separate 50-image OOD set
and exactly 20 independent positive images. It writes `ml/reports/evaluation.json` atomically and
adds the README results table only after a real frozen evaluation; no placeholder metrics are
reported.

Fast verification without models or CUDA:

```bash
cd ml
python -m pip install -r requirements-ci.txt
ruff check src tests
pytest -q -m 'not real_model'
```

### Backend handoff

Construct and warm one service per GPU worker during FastAPI lifespan startup, never at module
import time:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from raahein_ml.config import load_config
from raahein_ml.service import RecognitionService


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = RecognitionService(load_config())
    service.start()
    app.state.recognition = service
    yield
```

The Python contract is `RecognitionService.identify(PIL.Image) -> RecognitionResult`. A valid
low-evidence prediction is successful uncertainty and still contains ordered candidates:

```json
{
  "status": "uncertain",
  "strategy": "fusion",
  "candidates": [
    {
      "monument_id": "taj-mahal",
      "rank": 1,
      "ranking_score": 0.93,
      "fused_score": 0.93,
      "model_ranks": {"siglip": 1, "dinov2": 2, "clip": 1}
    }
  ],
  "artifact_version": "<artifact-id>"
}
```

`service.readiness.to_dict()` exposes load state, artifact version, device, loaded models and the
startup error, if any. Missing CUDA, checkpoints, indexes, thresholds or mismatched hashes raise
typed service/configuration errors and must map to a server error. They must never be translated to
`status: "uncertain"`. HTTP image decoding, MIME/size validation, multipart handling, rate limiting
and the existing API error envelope remain the backend route's responsibility.

## How we work

1. Create a branch from `main`: `git switch -c feat/short-name`.
2. Commit with conventional messages (`feat:`, `fix:`, `docs:`, `chore:`).
3. Push and open a pull request into `main`.
4. Merge only after CI passes and the code owner approves. Don't push to `main` directly.

## Team

| Name | Role |
|---|---|
| Utkarsh | MLOps (code owner) |
| Mridul | Backend + API |
| Harshit | Backend + Testing |
| Raunak | Frontend + Pipeline |

## Licence

_TODO: choose a licence._
