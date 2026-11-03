"""Rebuild the bundled travel matrices from the monuments in the DB (ORS if ORS_API_KEY is set, else OSRM)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.planner.matrix import (
    SUPPORTED_PROFILES,
    bundled_matrix_path,
    fetch_ors_matrix,
    fetch_osrm_matrix,
    read_monuments_from_db,
    save_matrix,
)

mons = read_monuments_from_db()
for profile in SUPPORTED_PROFILES:
    matrix = (fetch_ors_matrix if os.environ.get("ORS_API_KEY") else fetch_osrm_matrix)(mons, profile=profile)
    save_matrix(matrix, bundled_matrix_path(profile))
    print(profile, len(mons), "monuments via", matrix.source)
