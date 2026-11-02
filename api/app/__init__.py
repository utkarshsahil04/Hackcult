from pathlib import Path

# Allow app package to discover backend modules (such as app.planner)
_backend_app = Path(__file__).resolve().parents[2] / "backend" / "app"
if _backend_app.is_dir() and str(_backend_app) not in __path__:
    __path__.append(str(_backend_app))

