"""Independent route validator for verifying solver itineraries against ground truth matrices."""

from __future__ import annotations

import logging

from app.planner.models import (
    Itinerary,
    TravelMatrix,
    ValidationResult,
)

logger = logging.getLogger(__name__)

# Physical realism limits
MAX_DRIVING_SPEED_KMH = 150.0
MAX_WALKING_SPEED_KMH = 15.0
TOLERANCE_TIME_MIN = 0.05
TOLERANCE_DIST_M = 1.0


class RouteValidator:
    """Independently verifies itinerary validity, constraints, and timing without trusting solver totals."""

    def __init__(self, matrix: TravelMatrix) -> None:
        self.matrix = matrix

    def validate(
        self,
        itinerary: Itinerary,
        known_monuments: list[str] | set[str] | None = None,
        time_budget_minutes: float | None = None,
        visit_durations: dict[str, float] | None = None,
    ) -> ValidationResult:
        """Independently evaluate an itinerary.

        Checks:
        1. Location existence against known monuments / matrix.
        2. Route starts at the requested start monument.
        3. No forbidden duplicate visits exist.
        4. Valid travel matrix entries exist between all consecutive stops.
        5. Visit durations are non-negative and included.
        6. Recalculated total travel + visit time does not exceed the budget.
        7. Reported totals match independently recalculated totals.
        8. No impossible, fabricated, or physically unrealistic transitions exist.
        """
        errors: list[str] = []
        warnings: list[str] = []

        budget = (
            time_budget_minutes
            if time_budget_minutes is not None
            else itinerary.time_budget_min
        )
        known = set(known_monuments or self.matrix.monument_slugs)
        dur_map = dict(visit_durations or {})

        # Infeasible itinerary check
        if not itinerary.is_feasible:
            if itinerary.stops:
                errors.append(
                    f"Itinerary marked infeasible but contains {len(itinerary.stops)} stops"
                )
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                recalculated_total_time_min=0.0,
                recalculated_travel_time_min=0.0,
                recalculated_visit_time_min=0.0,
                recalculated_distance_m=0.0,
            )

        stops = itinerary.stops
        if not stops:
            errors.append("Feasible itinerary must have at least one stop")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # 1. Location existence
        for idx, s in enumerate(stops):
            if s.monument_slug not in known:
                errors.append(
                    f"Stop {idx} '{s.monument_slug}' is not an existing or valid monument"
                )

        # 2. Start location match
        if stops[0].monument_slug != itinerary.start_monument:
            errors.append(
                f"Itinerary starts at '{stops[0].monument_slug}', expected '{itinerary.start_monument}'"
            )

        # 3. Duplicate visits check
        if itinerary.return_to_start:
            if len(stops) > 1:
                if stops[-1].monument_slug != itinerary.start_monument:
                    errors.append(
                        f"Round-trip itinerary must end at start monument '{itinerary.start_monument}', "
                        f"got '{stops[-1].monument_slug}'"
                    )
                # Check intermediate stops
                intermediate = [s.monument_slug for s in stops[1:-1]]
                if len(intermediate) != len(set(intermediate)):
                    errors.append(
                        f"Duplicate visits detected in intermediate stops: {intermediate}"
                    )
                if itinerary.start_monument in intermediate:
                    errors.append(
                        f"Start monument '{itinerary.start_monument}' visited prematurely in intermediate stops"
                    )
        else:
            all_visited = [s.monument_slug for s in stops]
            if len(all_visited) != len(set(all_visited)):
                errors.append(
                    f"Forbidden duplicate visits in open tour: {all_visited}"
                )

        # 4 & 5. Travel matrix transitions, durations, and physical sanity
        recalc_travel_time_min = 0.0
        recalc_travel_dist_m = 0.0
        recalc_visit_time_min = 0.0

        for i in range(len(stops)):
            stop = stops[i]

            # Visit duration check
            if stop.visit_duration_min < 0:
                errors.append(
                    f"Stop {i} '{stop.monument_slug}' has negative visit duration: {stop.visit_duration_min}"
                )

            # If expected duration provided, verify
            if stop.monument_slug in dur_map:
                is_return_stop = (
                    itinerary.return_to_start
                    and i == len(stops) - 1
                    and i > 0
                )
                expected_v = 0.0 if is_return_stop else dur_map[stop.monument_slug]
                if abs(stop.visit_duration_min - expected_v) > TOLERANCE_TIME_MIN:
                    errors.append(
                        f"Stop {i} '{stop.monument_slug}' visit duration mismatch: "
                        f"got {stop.visit_duration_min}m, expected {expected_v}m"
                    )

            recalc_visit_time_min += stop.visit_duration_min

            # Transitions to next stop
            if i < len(stops) - 1:
                next_stop = stops[i + 1]
                from_s = stop.monument_slug
                to_s = next_stop.monument_slug

                if not self.matrix.has_route(from_s, to_s):
                    errors.append(
                        f"Missing matrix route between consecutive stops '{from_s}' -> '{to_s}'"
                    )
                    continue

                m_time_min = self.matrix.get_travel_time_minutes(from_s, to_s)
                m_dist_m = self.matrix.get_travel_distance_meters(from_s, to_s)

                # Check stop's recorded travel time vs matrix
                if abs(stop.travel_time_to_next_min - m_time_min) > TOLERANCE_TIME_MIN:
                    errors.append(
                        f"Transition {from_s} -> {to_s} travel time mismatch: "
                        f"stop reports {stop.travel_time_to_next_min}m, matrix has {m_time_min:.2f}m"
                    )

                if abs(stop.travel_distance_to_next_m - m_dist_m) > TOLERANCE_DIST_M:
                    errors.append(
                        f"Transition {from_s} -> {to_s} travel distance mismatch: "
                        f"stop reports {stop.travel_distance_to_next_m}m, matrix has {m_dist_m:.1f}m"
                    )

                # Check for impossible/fabricated transitions
                if m_dist_m > 500.0 and m_time_min <= 0.0:
                    errors.append(
                        f"Fabricated instantaneous travel ({m_dist_m:.0f}m in {m_time_min}m) "
                        f"between '{from_s}' and '{to_s}'"
                    )

                # Speed check
                if m_time_min > 0:
                    speed_kmh = (m_dist_m / 1000.0) / (m_time_min / 60.0)
                    if self.matrix.profile == "driving-car" and speed_kmh > MAX_DRIVING_SPEED_KMH:
                        errors.append(
                            f"Implausible driving speed {speed_kmh:.1f} km/h between '{from_s}' and '{to_s}'"
                        )
                    elif self.matrix.profile == "foot-walking" and speed_kmh > MAX_WALKING_SPEED_KMH:
                        errors.append(
                            f"Implausible walking speed {speed_kmh:.1f} km/h between '{from_s}' and '{to_s}'"
                        )

                recalc_travel_time_min += m_time_min
                recalc_travel_dist_m += m_dist_m
            else:
                # Last stop must have 0 travel to next
                if stop.travel_time_to_next_min != 0.0 or stop.travel_distance_to_next_m != 0.0:
                    warnings.append(
                        f"Final stop '{stop.monument_slug}' has non-zero forward travel values"
                    )

        # 6. Timeline progression verification
        if abs(stops[0].arrival_time_min - 0.0) > TOLERANCE_TIME_MIN:
            errors.append(
                f"Itinerary first stop arrival time must be 0.0, got {stops[0].arrival_time_min}"
            )

        for i in range(len(stops)):
            s = stops[i]
            expected_dep = round(s.arrival_time_min + s.visit_duration_min, 2)
            if abs(s.departure_time_min - expected_dep) > TOLERANCE_TIME_MIN:
                errors.append(
                    f"Stop {i} '{s.monument_slug}' departure mismatch: "
                    f"got {s.departure_time_min}, expected {expected_dep}"
                )

            if i < len(stops) - 1:
                next_s = stops[i + 1]
                expected_arr = round(s.departure_time_min + s.travel_time_to_next_min, 2)
                if abs(next_s.arrival_time_min - expected_arr) > TOLERANCE_TIME_MIN:
                    errors.append(
                        f"Stop {i+1} '{next_s.monument_slug}' arrival mismatch: "
                        f"got {next_s.arrival_time_min}, expected {expected_arr}"
                    )

        # 7. Independent total recalculation & budget verification
        recalc_total_time_min = round(recalc_visit_time_min + recalc_travel_time_min, 2)

        if recalc_total_time_min > budget + 1e-3:
            errors.append(
                f"Budget exceeded: recalculated total time {recalc_total_time_min:.2f}m "
                f"exceeds time budget of {budget:.2f}m"
            )

        # Verify reported solver totals against independently recalculated values
        if abs(itinerary.total_time_min - recalc_total_time_min) > TOLERANCE_TIME_MIN:
            errors.append(
                f"Solver reported total time ({itinerary.total_time_min:.2f}m) does not match "
                f"independently recalculated total time ({recalc_total_time_min:.2f}m)"
            )

        if abs(itinerary.total_travel_time_min - recalc_travel_time_min) > TOLERANCE_TIME_MIN:
            errors.append(
                f"Solver reported travel time ({itinerary.total_travel_time_min:.2f}m) does not match "
                f"independently recalculated travel time ({recalc_travel_time_min:.2f}m)"
            )

        if abs(itinerary.total_visit_time_min - recalc_visit_time_min) > TOLERANCE_TIME_MIN:
            errors.append(
                f"Solver reported visit time ({itinerary.total_visit_time_min:.2f}m) does not match "
                f"independently recalculated visit time ({recalc_visit_time_min:.2f}m)"
            )

        if abs(itinerary.total_travel_distance_m - recalc_travel_dist_m) > TOLERANCE_DIST_M:
            errors.append(
                f"Solver reported travel distance ({itinerary.total_travel_distance_m:.1f}m) does not match "
                f"independently recalculated travel distance ({recalc_travel_dist_m:.1f}m)"
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            recalculated_total_time_min=recalc_total_time_min,
            recalculated_travel_time_min=round(recalc_travel_time_min, 2),
            recalculated_visit_time_min=round(recalc_visit_time_min, 2),
            recalculated_distance_m=round(recalc_travel_dist_m, 1),
        )


def validate_itinerary(
    itinerary: Itinerary,
    matrix: TravelMatrix,
    known_monuments: list[str] | set[str] | None = None,
    time_budget_minutes: float | None = None,
    visit_durations: dict[str, float] | None = None,
) -> ValidationResult:
    """Convenience helper to independently validate an itinerary."""
    validator = RouteValidator(matrix)
    return validator.validate(
        itinerary,
        known_monuments=known_monuments,
        time_budget_minutes=time_budget_minutes,
        visit_durations=visit_durations,
    )

