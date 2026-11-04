"""Runs the Raahein API and photo recognition on Modal. Deploy from the repository root:

    modal deploy deploy/modal_app.py

See "Deployment" in the README for the whole process, including the secret this needs.
"""

import sys
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
REMOTE_ROOT = "/root/raahein"

# Both are gitignored, so deploying needs a machine that has them.
REQUIRED_LOCAL_FILES = (
    "backend/data/raahein.db",  # holds the generated stories
    "data/artifacts/dataset-v1/gates.json",  # the recognition artifact
)

# The artifact's active model, so only it is downloaded. Update this if gates.json changes model.
ACTIVE_MODEL = "facebook/dinov2-base"
ACTIVE_MODEL_REVISION = "f9e44c814b77203eaa57a6bdbbd535f21ede1415"  # as pinned in ml/config/models.yaml

if modal.is_local():
    missing = [path for path in REQUIRED_LOCAL_FILES if not (ROOT / path).is_file()]
    if missing:
        sys.exit(f"Can't deploy, because these files are missing: {', '.join(missing)}")

SKIP = ["**/__pycache__/**", "**/.pytest_cache/**", "**/.ruff_cache/**", "**/tests/**", "**/*.bak", "**/.env"]

image = (
    modal.Image.debian_slim(python_version="3.12")
    # The CPU build of PyTorch must come first: the default one is several GB larger, for a GPU we don't have.
    .pip_install("torch==2.5.1", index_url="https://download.pytorch.org/whl/cpu")
    .pip_install_from_requirements(str(ROOT / "api" / "requirements.txt"))
    .pip_install_from_pyproject(str(ROOT / "ml" / "pyproject.toml"), optional_dependencies=["gpu"])
    .run_commands(
        "python -c \"from huggingface_hub import snapshot_download; "
        f"snapshot_download('{ACTIVE_MODEL}', revision='{ACTIVE_MODEL_REVISION}', "
        "allow_patterns=['*.json', 'model.safetensors'])\"",
        env={"HF_HOME": "/root/huggingface"},
    )
    .add_local_dir(ROOT / "api", f"{REMOTE_ROOT}/api", copy=True, ignore=SKIP)
    .add_local_dir(ROOT / "backend", f"{REMOTE_ROOT}/backend", copy=True, ignore=SKIP)
    .add_local_dir(ROOT / "ml", f"{REMOTE_ROOT}/ml", copy=True, ignore=SKIP)
    .add_local_dir(ROOT / "data" / "artifacts" / "dataset-v1", f"{REMOTE_ROOT}/data/artifacts/dataset-v1", copy=True)
    .run_commands(f"pip install --no-deps -e {REMOTE_ROOT}/ml")
    .env({"HF_HOME": "/root/huggingface", "RAAHEIN_ML_DEVICE": "cpu", "RAAHEIN_ML_ALLOW_CPU": "true"})
    .workdir(f"{REMOTE_ROOT}/api")
)

app = modal.App("raahein", image=image)


@app.function(
    secrets=[modal.Secret.from_name("raahein")],  # GEMINI_API_KEY and FRONTEND_ORIGIN
    cpu=1.0,
    memory=2048,  # the API and model use about 0.9 GB
    max_containers=1,  # keeps the rate limit counts in one place and spending predictable
    scaledown_window=900,  # stays awake 15 minutes after the last request, so a browsing visitor sees one wake-up
    timeout=120,
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def api():
    sys.path.insert(0, f"{REMOTE_ROOT}/api")
    from app.main import app as web_app

    return web_app
