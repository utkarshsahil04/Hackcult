# Raahein

> Photograph a monument. Discover its story, explore it in 3D, and follow the
> historical threads that connect it to other places in India.

Built for **HackCult '26** (Track: Culture & Digital Heritage). Covers 28 sites in Delhi and Agra:
15 with sourced stories, and 13 that can be planned and mapped while their stories are pending.

**Try it live: [hackcult-drab.vercel.app](https://hackcult-drab.vercel.app/)**

The web app runs on Vercel, and the API and photo recognition run on Modal
([API health](https://utkarsh-sahil04--raahein-api.us-east.modal.run/api/health)). The API sleeps when idle, so the
first request after a quiet spell can take up to about a minute.

## Quick start

You need Python 3.12, Node 22 and pnpm. From the repository root, run:

```
python dev.py
```

That's the only command you need. It starts the web app at http://localhost:3000 and the API at
http://localhost:8000/docs, and Ctrl+C stops both.

The first run asks for your `GEMINI_API_KEY` and then sets everything up, which takes a few minutes.
Later runs only redo what has changed.

If your default Python isn't 3.12, use `py -3.12 dev.py` the first time.

### Optional extras

Add these once, when you want them:

| Command | What it adds |
|---|---|
| `python dev.py --stories` | Generates stories with Gemini. Without them, `/api/stories/{slug}` returns a 404. |
| `python dev.py --recognition` | Installs photo recognition (a large download). |

**Stories** take at least 8 minutes because of free-tier rate limits. The 13 story-pending sites have
no sourced claims, so they report `[FAIL]`. That's expected.

**Recognition** also needs the artifact in `data\artifacts\dataset-v1`. If you don't have one, build
it from the `Indian-monuments` dataset, which downloads the models on the first run:

```powershell
.venv\Scripts\python -m raahein_ml.dataset_pipeline build --dataset <path>\Indian-monuments\images
```

`http://localhost:8000/api/health` shows `"models":"ok"` when it's ready. It uses your NVIDIA GPU if
you have one, otherwise the CPU. It recognises 7 monuments: Taj Mahal, Humayun's Tomb, Fatehpur
Sikri, Qutb complex, Mehrauli Archaeological Park, India Gate and Lotus Temple. Other monuments
usually come back "uncertain", but not always: in a 24-photo Wikimedia check of Red Fort, Agra Fort,
Purana Qila, Jama Masjid and Safdarjung's Tomb, 4 were still wrongly accepted. The dataset's licence
is unconfirmed, so this is for the demo only.

## Features

- **Recognition:** identify a monument from a photo, or say when it isn't sure
- **Stories:** sourced narratives in English and Hindi, with narration
- **3D:** explore a monument's architecture through clickable hotspots
- **Connections:** links between monuments through dynasties, rulers, events and styles
- **Plan your day:** solver-built routes of up to 5 stops, shown on the map, each checked by an independent validator
- **Nearby:** the closest monuments to you, with distances
- **My journey:** record the monuments you've visited and see your path, with no account

## Tech stack

| Part | Tools |
|---|---|
| Frontend | Next.js 16 PWA, pnpm, Playwright |
| API | FastAPI |
| Recognition | DINOv2, SigLIP and CLIP embeddings |
| Stories | Gemini, generated in advance and stored in the database |
| Data | SQLite, built from JSON seed files |
| Maps and routes | OpenStreetMap, Overpass, OSRM or OpenRouteService, OR-Tools |

## Project layout

```
dev.py      Sets up and runs everything
deploy/     Hosting setup and a check for a running API
frontend/   Next.js web app
api/        FastAPI HTTP application
backend/    SQLite heritage data, tour planner and data tools
ml/         Recognition package, manifests and config
data/       Ignored images, caches and generated recognition artifacts
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Status of the API and its models |
| POST | `/api/recognition/identify` | Identify a photo (multipart field `photo`, 6 MB max) |
| GET | `/api/monuments/{slug}` | Monument profile with sourced claims |
| GET | `/api/monuments/{slug}/related` | Connected monuments |
| GET | `/api/stories/{slug}` | Generated story |
| GET | `/api/places/nearby` | Places near a monument |
| POST | `/api/tours/plan` | Build a day plan of up to 5 stops |
| POST | `/api/tours/route-line` | Road shape between a plan's stops |

## Configuration

All settings live in `.env` at the repository root, which `dev.py` creates for you:

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Stories and free-text plan queries |
| `FRONTEND_ORIGIN` | No | Allowed web app origin (default `http://localhost:3000`) |
| `SQLITE_DB_PATH` | No | Database location, relative to `backend\` |

The web app reads one setting from its host's environment:

| Variable | Required | Purpose |
|---|---|---|
| `NEXT_PUBLIC_SITE_URL` | In production | Public address, used for canonical links, the sitemap and sharing previews |

## Tests

From the repository root:

```powershell
.venv\Scripts\python -m pytest api
.venv\Scripts\python -m pytest backend
.venv\Scripts\python -m pytest ml -m "not real_model"
.venv\Scripts\python -m ruff check backend ml\src ml\tests
pnpm -C frontend typecheck
pnpm -C frontend lint
pnpm -C frontend test:unit
pnpm -C frontend test:e2e
```

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Port 8000 is already in use` | An old server is still running. Close it and try again. |
| `identify` returns 500 and health shows `"models":"error"` | Recognition isn't installed, the artifact is missing, or Windows is low on memory. The server log has the exact error. |
| `identify` returns 405 | It only accepts POST, so it can't be opened in a browser. |
| A hosted site says it can't reach the API | Check that `FRONTEND_ORIGIN` on Modal exactly matches the Vercel address, with no trailing `/`. |
| `paging file is too small` in the log | Close other heavy programs, or increase the Windows page file. |
| `/api/stories/{slug}` returns 404 | Run `python dev.py --stories`. |

## Deployment

This setup is free to run: Vercel hosts the web app, and Modal hosts the API and recognition model together. Modal's container sleeps when idle, so the first visitor after a quiet spell waits for it to wake, up to about a minute.

Deploy the API from a machine that has `backend/data/raahein.db` and `data/artifacts/dataset-v1`, because both are gitignored.

```powershell
pip install modal
modal setup
modal secret create raahein GEMINI_API_KEY=your-key FRONTEND_ORIGIN=http://localhost:3000
modal deploy deploy/modal_app.py
```

The last command prints the API's address. Check it with:

```powershell
.venv\Scripts\python deploy/smoke_test.py https://your-api-address path\to\photo.jpg
```

In Vercel, import the repository and set **Root Directory** to `frontend`. Add these environment variables, then deploy:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | The Modal address |
| `NEXT_PUBLIC_SITE_URL` | The Vercel address |

Finally, allow the Vercel address to call the API, and redeploy:

```powershell
modal secret create raahein GEMINI_API_KEY=your-key FRONTEND_ORIGIN=https://your-app.vercel.app --force
modal deploy deploy/modal_app.py
```

Never add a payment method to the Modal account if it must stay free. Its free monthly credit covers roughly 475 running hours at this size.

## More documentation

- [Plan architecture](backend/docs/PLAN_ARCHITECTURE.md): configure plans and add locations
- [Profile architecture](backend/docs/PROFILE_ARCHITECTURE.md): the plan for accounts, sharing and tour guides
- [Seed data](backend/app/db/seed_data/README.md): data files and sourcing rules
- [Recognition pipeline](ml/README.md): architecture, licensed-data workflow and service contract

## Contributing

1. Install the secret check once: `pip install pre-commit`, then `pre-commit install`.
2. Create a branch from `Dev`: `git switch -c feat/short-name`.
3. Commit with conventional messages (`feat:`, `fix:`, `docs:`, `chore:`).
4. Open a pull request into `Dev`. Merge only after CI passes and the code owner approves.

Never commit `.env` files. Every historical claim needs two sources from different publishers, and
legends must be flagged `is_legend`.

## Team

| Name | Role |
|---|---|
| Utkarsh | MLOps (code owner) |
| Mridul | Backend + API |
| Harshit | Backend + Testing |
| Raunak | Frontend + Pipeline |

## Licence

_TODO: choose a licence._
