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
backend/    FastAPI app (requirements.txt)
frontend/   Next.js app (pnpm; needs typecheck, lint and build scripts)
.github/    CI workflow and CODEOWNERS
```

CI runs the backend and frontend checks as soon as those folders exist.

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
