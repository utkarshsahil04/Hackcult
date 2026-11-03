"""Planner evaluation: travel-matrix quality plus feasibility/optimality over a scenario grid.

Every scenario is solved by OR-Tools, checked by the independent RouteValidator, and graded against
the exhaustive-search optimum. Usage: python tools/evaluate_planner.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.planner.config import preset_names, resolve_config, restrict_legs  # noqa: E402
from app.planner.exhaustive import best_plan  # noqa: E402
from app.planner.matrix import load_matrix, read_monuments_from_db  # noqa: E402
from app.planner.solver import solve_itinerary  # noqa: E402
from app.planner.validator import validate_itinerary  # noqa: E402

BUDGETS = (90, 120, 180, 240, 360)
PROFILES = ("driving-car", "foot-walking")


def matrix_quality(matrix) -> dict:
    n = len(matrix.monument_slugs)
    d = matrix.durations
    pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
    routable = [(i, j) for i, j in pairs if d[i][j] is not None]
    asym = [abs(d[i][j] - d[j][i]) / max(d[i][j], d[j][i], 1) for i, j in routable if d[j][i] is not None]
    tri = sum(
        1 for i, j in routable for k in range(n)
        if k not in (i, j) and d[i][k] is not None and d[k][j] is not None and d[i][j] > (d[i][k] + d[k][j]) * 1.25
    )
    return {
        "profile": matrix.profile, "source": matrix.source, "nodes": n,
        "routable_pairs_pct": round(100 * len(routable) / len(pairs), 1),
        "median_asymmetry_pct": round(100 * statistics.median(asym), 1) if asym else 0.0,
        "triangle_violations_over_25pct": tri,
    }


def evaluate(city: str | None = "Delhi") -> dict:
    rows = read_monuments_from_db()
    slugs = [r["slug"] for r in rows]
    pool = [r["slug"] for r in rows if not city or r["city"].lower() == city.lower()]
    runs, quality = [], []
    for profile in PROFILES:
        base = load_matrix(profile=profile)
        quality.append(matrix_quality(base))
        for preset in preset_names():
            cfg = resolve_config(preset)
            matrix = restrict_legs(base, cfg.max_leg_min)
            visit = {s: float(cfg.visit_minutes(s)) for s in slugs}
            for budget in BUDGETS:
                for start in pool:
                    t0 = time.perf_counter()
                    it = solve_itinerary(start, budget, matrix, candidate_slugs=pool, max_stops=cfg.max_stops,
                                         visit_durations=visit, time_limit_seconds=1)
                    ms = (time.perf_counter() - t0) * 1000
                    oracle = best_plan(matrix, budget, cfg.max_stops, visit, pool, start=start)
                    verdict = validate_itinerary(it, matrix=matrix, time_budget_minutes=budget, visit_durations=visit) if it.is_feasible else None
                    runs.append({
                        "profile": profile, "preset": preset, "budget": budget, "start": start,
                        "feasible": it.is_feasible, "oracle_feasible": oracle is not None,
                        "valid": bool(verdict and verdict.is_valid), "stops": len(it.stops),
                        "optimal": (it.is_feasible and len(it.stops) == len(oracle[1]) and it.total_time_min <= -oracle[0][1] + 1.0) if oracle else not it.is_feasible,
                        "time_gap_min": max(0.0, it.total_time_min + oracle[0][1]) if oracle and it.is_feasible else 0.0,
                        "util": it.total_time_min / budget if it.is_feasible else 0.0,
                        "travel_share": it.total_travel_time_min / it.total_time_min if it.is_feasible and it.total_time_min else 0.0,
                        "ms": ms,
                    })
    feas = [r for r in runs if r["feasible"]]
    summary = {
        "scenarios": len(runs),
        "feasible_pct": round(100 * len(feas) / len(runs), 1),
        "feasible_when_possible_pct": round(100 * sum(r["feasible"] for r in runs if r["oracle_feasible"]) / max(1, sum(r["oracle_feasible"] for r in runs)), 1),
        "validator_pass_pct": round(100 * sum(r["valid"] for r in feas) / max(1, len(feas)), 1),
        "max_stops_seen": max((r["stops"] for r in runs), default=0),
        "optimal_pct": round(100 * sum(r["optimal"] for r in runs) / len(runs), 1),
        "max_time_gap_min": round(max(r["time_gap_min"] for r in runs), 2),
        "mean_budget_utilisation_pct": round(100 * statistics.mean(r["util"] for r in feas), 1) if feas else 0.0,
        "mean_travel_share_pct": round(100 * statistics.mean(r["travel_share"] for r in feas), 1) if feas else 0.0,
        "p95_solve_ms": round(sorted(r["ms"] for r in runs)[int(0.95 * len(runs)) - 1], 1),
    }
    by_preset = {
        p: {
            "feasible_pct": round(100 * sum(r["feasible"] for r in runs if r["preset"] == p) / sum(r["preset"] == p for r in runs), 1),
            "mean_stops": round(statistics.mean(r["stops"] for r in runs if r["preset"] == p and r["feasible"]), 2),
        } for p in preset_names()
    }
    return {"matrix": quality, "summary": summary, "by_preset": by_preset}


if __name__ == "__main__":
    report = evaluate()
    print(json.dumps(report, indent=1))
