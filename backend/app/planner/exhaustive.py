"""Exact best plan by depth-first search with branch and bound.

Checking every ordering stops scaling at 5 stops (about 4.4 million routes from 23 sites), so branches
that provably can't beat the best plan so far are cut. The result is still exact, which keeps this both
the oracle the OR-Tools solver is graded against and the way to pick a start when none is given.
"""

from __future__ import annotations

from bisect import bisect_left
from itertools import accumulate

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
    if max_stops < 1 or not must <= set(pool) or (start and start not in pool):
        return None

    size = len(pool)
    visit = [visit_min[s] for s in pool]
    weight = [1 + prio.get(s, 0) for s in pool]
    required = sum(1 << i for i, s in enumerate(pool) if s in must)
    legs = [
        sorted(
            (
                (matrix.get_travel_time_minutes(a, b), j)
                for j, b in enumerate(pool)
                if j != i and matrix.has_route(a, b)
            ),
            key=lambda leg: leg[0] + visit[leg[1]],  # cheap stops first, so a strong plan is found early
        )
        for i, a in enumerate(pool)
    ]
    # Least time any further stop can add, and the most any n further stops can score.
    shortest = min((leg + visit[j] for options in legs for leg, j in options), default=float("inf"))
    best_gain = [0, *accumulate(sorted(weight, reverse=True))]

    best_weight, best_total = 0, float("inf")
    best_route: list[int] = []
    route: list[int] = []

    def search(last: int, used: int, score: int, total: float) -> None:
        nonlocal best_weight, best_total, best_route
        missing = required & ~used
        if not missing and (score > best_weight or (score == best_weight and total < best_total)):
            best_weight, best_total, best_route = score, total, route.copy()

        stops_left = max_stops - len(route)
        affordable = min(stops_left, int((budget_min - total) / shortest + 1e-9), size - len(route))
        if affordable < missing.bit_count():
            return
        reachable = score + best_gain[affordable]
        if reachable < best_weight:
            return
        if reachable == best_weight:  # can only tie on score, so it must also be faster
            still_needed = bisect_left(best_gain, best_weight - score)
            if total + still_needed * shortest >= best_total:
                return

        for leg, j in legs[last]:
            bit = 1 << j
            arrival = total + leg + visit[j]
            if used & bit or arrival > budget_min:
                continue
            route.append(j)
            search(j, used | bit, score + weight[j], arrival)
            route.pop()

    starts = [pool.index(start)] if start else sorted(range(size), key=visit.__getitem__)
    for i in starts:
        if visit[i] <= budget_min:
            route.append(i)
            search(i, 1 << i, weight[i], visit[i])
            route.pop()

    return ((best_weight, -best_total), [pool[i] for i in best_route]) if best_route else None
