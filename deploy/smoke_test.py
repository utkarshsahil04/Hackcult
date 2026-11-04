"""Checks a running API end to end. Usage: python deploy/smoke_test.py https://your-api-address [photo.jpg]

Exits non-zero if anything a visitor depends on is broken. Allows for a cold start on the first request.
"""

import sys

import httpx

COLD_START_SECONDS = 150


def run_checks(base: str, photo: str | None = None) -> list[str]:
    """Return one line for each failed check."""
    failures: list[str] = []

    def check(name: str, passed: bool, detail: object = "") -> None:
        print(f"{'ok  ' if passed else 'FAIL'} {name}{f': {detail}' if detail and not passed else ''}")
        if not passed:
            failures.append(name)

    with httpx.Client(base_url=base.rstrip("/"), timeout=COLD_START_SECONDS) as client:
        systems = client.get("/api/health").json()["subsystems"]
        check("database is readable", systems["database"] == "ok", systems)
        check("recognition model is loaded", systems["models"] == "ok", systems)

        monument = client.get("/api/monuments/taj-mahal")
        check("monument details load", monument.status_code == 200, monument.status_code)
        story = client.get("/api/stories/taj-mahal")
        check("stories are included", story.status_code == 200, story.status_code)

        plan = client.post("/api/tours/plan", json={
            "time_budget_minutes": 600, "preset": "quick", "max_stops": 5, "profile": "driving-car",
            "preferences": {"city": "Delhi"}, "time_limit_seconds": 1,
        })
        body = plan.json() if plan.status_code == 200 else {}
        stops = [stop["monument_slug"] for stop in body.get("itinerary", {}).get("stops", [])]
        check("a 5-stop plan is built and validated", body.get("is_validated") is True and len(stops) == 5, plan.status_code)

        line = client.post("/api/tours/route-line", json={"stops": stops, "profile": "driving-car"})
        check("the route line is returned", line.status_code == 200 and len(line.json().get("legs", [])) == len(stops) - 1, line.status_code)
        if line.status_code == 200 and line.json().get("source") != "roads":
            print("note road shapes are unavailable, so straight lines are being used")

        if photo:
            with open(photo, "rb") as file:
                found = client.post("/api/recognition/identify", files={"photo": ("photo.jpg", file, "image/jpeg")})
            check("a photo is identified", found.status_code == 200 and found.json().get("status") in ("ok", "uncertain"), found.status_code)
    return failures


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    failed = run_checks(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"\n{len(failed)} check(s) failed" if failed else "\nAll checks passed")
    sys.exit(1 if failed else 0)
