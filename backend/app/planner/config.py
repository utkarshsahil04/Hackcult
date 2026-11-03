"""Configurable plan architecture: presets + overrides resolve to one immutable PlanConfig.

Add a preset or retune visit times by editing data/plan_presets.json; no code change needed.
The hard stop cap (3) lives in the same file and can never be exceeded by a request.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.planner.models import InvalidInputError, TravelMatrix

PRESETS_PATH = Path(__file__).with_name("data") / "plan_presets.json"


@lru_cache(maxsize=1)
def _raw() -> dict[str, Any]:
    return json.loads(PRESETS_PATH.read_text(encoding="utf-8"))


def preset_names() -> list[str]:
    return list(_raw()["presets"])


@dataclass(frozen=True)
class PlanConfig:
    preset: str
    max_stops: int
    max_leg_min: float
    visit_scale: float

    def visit_minutes(self, slug: str, listed: bool = False) -> float:
        v = _raw()["visit_minutes"]
        base = v["by_slug"].get(slug, v["listed_default"] if listed else v["default"])
        return round(base * self.visit_scale)


def resolve_config(
    preset: str | None = None, max_stops: int | None = None, max_leg_min: float | None = None
) -> PlanConfig:
    raw = _raw()
    name = preset or raw["default_preset"]
    if name not in raw["presets"]:
        raise InvalidInputError(f"Unknown plan preset '{name}'. Available: {preset_names()}")
    p = raw["presets"][name]
    cap = raw["hard_max_stops"]
    stops = min(max_stops if max_stops else p["max_stops"], cap)
    return PlanConfig(name, stops, max_leg_min or p["max_leg_min"], p["visit_scale"])


def restrict_legs(matrix: TravelMatrix, max_leg_min: float) -> TravelMatrix:
    """Copy of the matrix where legs longer than max_leg_min are unroutable (solver and validator agree)."""
    limit = max_leg_min * 60

    def keep(i: int, j: int, v: float | None) -> float | None:
        return None if v is None or (i != j and v > limit) else v

    n = len(matrix.monument_slugs)
    durations = [[keep(i, j, matrix.durations[i][j]) for j in range(n)] for i in range(n)]
    distances = [
        [None if durations[i][j] is None else matrix.distances[i][j] for j in range(n)] for i in range(n)
    ]
    return TravelMatrix(
        profile=matrix.profile, monument_slugs=matrix.monument_slugs, locations=matrix.locations,
        durations=durations, distances=distances, created_at=matrix.created_at, source=matrix.source,
    )


def interest_priorities(rows: list[dict[str, Any]], interests: list[str]) -> dict[str, int]:
    """+1 priority per interest keyword found in a monument's name, era or style (case-insensitive).
    The keyword 'legend' matches monuments that have a recorded legend (rows with has_legend)."""
    words = [w.strip().lower() for w in interests if w.strip()]
    return {
        r["slug"]: n
        for r in rows
        if (n := sum(w in f"{r['name']} {r['era']} {r['architectural_style']} {'legend' if r.get('has_legend') else ''}".lower() for w in words))
    }
