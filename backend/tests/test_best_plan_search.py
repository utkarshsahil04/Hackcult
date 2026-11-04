import random
import time
from itertools import pairwise, permutations

import pytest

from app.planner.exhaustive import best_plan
from app.planner.matrix import load_matrix
from app.planner.models import TravelMatrix


def _matrix(rng: random.Random, size: int) -> tuple[TravelMatrix, list[str]]:
    slugs = [f"s{i}" for i in range(size)]
    durations = [[0 if i == j else (None if rng.random() < 0.15 else rng.randint(3, 70) * 60.0) for j in range(size)] for i in range(size)]
    distances = [[None if v is None else v * 8 for v in row] for row in durations]
    locations = [[77 + i / 10, 28.0] for i in range(size)]
    return TravelMatrix("driving-car", slugs, locations, durations, distances, "2026-01-01T00:00:00Z"), slugs


def _every_ordering(matrix, budget, max_stops, visit, pool, start, must, prio):
    """The old check of every ordering, kept here as the reference the fast search must match."""
    best = None
    for k in range(1, max_stops + 1):
        for route in permutations(pool, k):
            if (start and route[0] != start) or not must <= set(route):
                continue
            if any(not matrix.has_route(a, b) for a, b in pairwise(route)):
                continue
            total = sum(matrix.get_travel_time_minutes(a, b) for a, b in pairwise(route)) + sum(visit[s] for s in route)
            if total > budget:
                continue
            score = (sum(1 + prio.get(s, 0) for s in route), -total)
            if best is None or score > best:
                best = score
    return best


@pytest.mark.parametrize("seed", range(120))
def test_search_matches_checking_every_ordering(seed):
    rng = random.Random(seed)
    matrix, slugs = _matrix(rng, rng.randint(2, 7))
    visit = {s: rng.choice([25, 40, 60, 90]) for s in slugs}
    budget = rng.choice([30, 60, 120, 200, 300, 600])
    max_stops = rng.randint(1, 5)
    start = rng.choice([None, slugs[0]])
    must = set(rng.sample(slugs, rng.randint(0, 2))) if rng.random() < 0.4 else set()
    prio = {s: rng.randint(1, 3) for s in slugs if rng.random() < 0.3}

    found = best_plan(matrix, budget, max_stops, visit, slugs, start=start, must_visit=must, priorities=prio)
    expected = _every_ordering(matrix, budget, max_stops, visit, slugs, start, must, prio)

    if expected is None:
        assert found is None
        return
    assert found[0][0] == expected[0]
    assert found[0][1] == pytest.approx(expected[1])
    route = found[1]
    assert len(route) <= max_stops and must <= set(route) and (not start or route[0] == start)
    assert all(matrix.has_route(a, b) for a, b in pairwise(route))


def test_five_stops_stays_fast_on_the_real_delhi_matrix():
    matrix = load_matrix(profile="driving-car")
    pool = matrix.monument_slugs
    visit = dict.fromkeys(pool, 45.0)
    began = time.perf_counter()
    score, route = best_plan(matrix, 600, 5, visit, pool)
    assert time.perf_counter() - began < 1.0
    assert score[0] == 5 and len(route) == 5


def test_impossible_requests_return_nothing():
    matrix = load_matrix(profile="driving-car")
    pool = matrix.monument_slugs[:6]
    visit = dict.fromkeys(pool, 45.0)
    assert best_plan(matrix, 10, 5, visit, pool) is None
    assert best_plan(matrix, 600, 0, visit, pool) is None
    assert best_plan(matrix, 600, 5, visit, pool, start="not-in-pool") is None
    assert best_plan(matrix, 600, 5, visit, pool, must_visit={"not-in-pool"}) is None
    assert best_plan(matrix, 600, 1, visit, pool, must_visit=set(pool[:2])) is None
