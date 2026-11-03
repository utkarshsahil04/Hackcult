"""Exact best plan by enumeration. With at most 3 stops this is instant, so it is both the
oracle the OR-Tools solver is graded against and the way to pick a start when none is given."""

from __future__ import annotations

from itertools import permutations

from app.planner.models import TravelMatrix


def best_plan(
    matrix: TravelMatrix,
    budget_min: float,
    max_stops: int,
    visit_min: dict[str, float],
    candidates: list[str],
    start: str | None = None,
    must_visit: set[str] | None = None,
    priorities: dict[str, int] | None = None,
) -> tuple[tuple[int, float], list[str]] | None:
    """Return ((weighted visits, -total minutes), ordered slugs) of the optimum, or None if infeasible."""
    must, prio = must_visit or set(), priorities or {}
    pool = [s for s in candidates if s in matrix.monument_slugs]
    best: tuple[tuple[int, float], list[str]] | None = None
    for k in range(1, max_stops + 1):
        for route in permutations(pool, k):
            if (start and route[0] != start) or not must <= set(route):
                continue
            if any(not matrix.has_route(a, b) for a, b in zip(route, route[1:], strict=False)):
                continue
            travel = sum(matrix.get_travel_time_minutes(a, b) for a, b in zip(route, route[1:], strict=False))
            total = travel + sum(visit_min[s] for s in route)
            if total > budget_min:
                continue
            score = (sum(1 + prio.get(s, 0) for s in route), -total)
            if best is None or score > best[0]:
                best = (score, list(route))
    return best
