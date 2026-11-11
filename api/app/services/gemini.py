from __future__ import annotations

import base64
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import get_settings
from app.planner.models import Itinerary

logger = logging.getLogger("raahein.api.gemini")

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.5-flash"  # tour planner keeps its current model


MONUMENT_KEYWORDS: dict[str, str] = {
    "taj": "taj-mahal",
    "agra fort": "agra-fort",
    "fatehpur": "fatehpur-sikri",
    "sikri": "fatehpur-sikri",
    "itimad": "itimad-ud-daulah",
    "i'timad": "itimad-ud-daulah",
    "baby taj": "itimad-ud-daulah",
    "akbar": "akbars-tomb",
    "sikandra": "akbars-tomb",
    "qutb": "qutb-complex",
    "qutub": "qutb-complex",
    "humayun": "humayuns-tomb",
    "red fort": "red-fort",
    "lal qila": "red-fort",
    "jama masjid": "jama-masjid",
    "india gate": "india-gate",
    "lotus": "lotus-temple",
    "bahai": "lotus-temple",
    "purana qila": "purana-qila",
    "old fort": "purana-qila",
    "safdarjung": "safdarjungs-tomb",
    "jantar mantar": "jantar-mantar",
    "tughlaqabad": "tughlaqabad-fort",
    "mehrauli": "mehrauli-archaeological-park",
    "lodhi": "lodhi-gardens",
    "hauz khas": "hauz-khas-complex",
    "agrasen": "agrasen-ki-baoli",
    "feroz shah": "feroz-shah-kotla",
    "rashtrapati": "rashtrapati-bhavan",
    "sunder nursery": "sunder-nursery",
    "khan-i-khana": "abdul-rahim-khan-i-khana-tomb",
    "khirki": "khirki-masjid",
    "nizamuddin": "nizamuddin-dargah",
    "raj ghat": "raj-ghat",
    "akshardham": "akshardham-delhi",
    "fatehpuri": "fatehpuri-masjid",
}

# Defaults to every slug the keywords can reach; routes/tours.py refreshes it from the monuments table.
VALID_SLUGS: list[str] = sorted(set(MONUMENT_KEYWORDS.values()))


@dataclass
class ParsedConstraints:
    """Structured constraints extracted from natural-language tour preferences."""

    start_monument: str | None = None
    time_budget_minutes: float | None = None
    must_visit: list[str] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    profile: str = "driving-car"
    return_to_start: bool = False
    max_stops: int | None = None
    visit_durations: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_monument": self.start_monument,
            "time_budget_minutes": self.time_budget_minutes,
            "must_visit": self.must_visit,
            "preferences": self.preferences,
            "profile": self.profile,
            "return_to_start": self.return_to_start,
            "max_stops": self.max_stops,
            "visit_durations": self.visit_durations,
        }


class GeminiService:
    """Service wrapping Google Gemini API for preference extraction and tour narration.

    Designed with graceful fallbacks so the tour planner can operate reliably even
    if Gemini is unconfigured or upstream requests fail.
    """

    def __init__(self, api_key: str | None = None, http_client: httpx.Client | None = None) -> None:
        if api_key is not None:
            self.api_key = api_key
        else:
            try:
                self.api_key = get_settings().gemini_api_key
            except (ValueError, KeyError, AttributeError):
                self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self._client = http_client

    def _call_gemini(
        self,
        prompt: str,
        timeout: float = 10.0,
        model: str | None = None,
        max_output_tokens: int = 800,
    ) -> str:
        """Call Gemini REST API generateContent. Raises RuntimeError on failure."""
        if not self.api_key or self.api_key in ("test-key", "placeholder", "your-api-key"):
            raise RuntimeError("Gemini API key is unconfigured or dummy.")

        url = f"{GEMINI_BASE_URL}/{model or DEFAULT_MODEL}:generateContent"
        headers = {"x-goog-api-key": self.api_key}  # header, so the key never lands in URLs or logs
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_output_tokens},
        }

        client = self._client or httpx.Client(timeout=timeout)
        try:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API returned status {resp.status_code}: {resp.text}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini API returned no candidates.")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts or "text" not in parts[0]:
                raise RuntimeError("Gemini API returned no text in candidate.")
            return parts[0]["text"].strip()
        finally:
            if self._client is None:
                client.close()

    def describe_image(self, image: bytes, mime: str, prompt: str, model: str, timeout: float = 60.0) -> str:
        """Send one image inline with a prompt and return the JSON text. Raises RuntimeError on failure."""
        if not self.api_key or self.api_key in ("test-key", "placeholder", "your-api-key"):
            raise RuntimeError("Gemini API key is unconfigured or dummy.")
        payload = {
            "contents": [{"parts": [
                {"inline_data": {"mime_type": mime, "data": base64.b64encode(image).decode()}},
                {"text": prompt},
            ]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4000, "responseMimeType": "application/json"},
        }
        client = self._client or httpx.Client(timeout=timeout)
        try:
            resp = client.post(
                f"{GEMINI_BASE_URL}/{model}:generateContent", json=payload, headers={"x-goog-api-key": self.api_key}
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API returned status {resp.status_code}")
            parts = (resp.json().get("candidates") or [{}])[0].get("content", {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            if not text.strip():
                raise RuntimeError("Gemini API returned no text.")
            return text.strip()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Gemini request failed: {type(exc).__name__}") from exc
        finally:
            if self._client is None:
                client.close()

    def parse_preferences(self, text: str) -> ParsedConstraints:
        """Parse natural language visitor preferences into structured constraints."""
        if not text or not text.strip():
            return ParsedConstraints()

        # Try Gemini API if available
        try:
            prompt = (
                "You are an assistant for Raahein Heritage Discovery. "
                "Parse the visitor's travel request into exact JSON constraints for a vehicle routing solver.\n"
                f"Valid monument slugs: {json.dumps(VALID_SLUGS)}\n"
                "Return ONLY a JSON object with this exact structure:\n"
                "{\n"
                '  "start_monument": "<slug or null>",\n'
                '  "time_budget_minutes": <number or null>,\n'
                '  "must_visit": ["<slug>", ...],\n'
                '  "city": "<Delhi or Agra or null>",\n'
                '  "profile": "<driving-car or foot-walking>",\n'
                '  "return_to_start": <true or false>,\n'
                '  "max_stops": <integer or null>\n'
                "}\n"
                f"User request: {text.strip()}\n"
            )
            raw = self._call_gemini(prompt)
            # Strip potential markdown code blocks
            clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
            parsed = json.loads(clean)

            start = parsed.get("start_monument")
            if start and start not in VALID_SLUGS:
                start = self._match_monument(start)

            must_visit = []
            for m in parsed.get("must_visit", []):
                matched = m if m in VALID_SLUGS else self._match_monument(m)
                if matched and matched not in must_visit:
                    must_visit.append(matched)

            budget = parsed.get("time_budget_minutes")
            if budget is not None:
                try:
                    budget = float(budget)
                    if budget <= 0:
                        budget = None
                except (ValueError, TypeError):
                    budget = None

            prefs: dict[str, Any] = {}
            if parsed.get("city"):
                prefs["city"] = str(parsed["city"]).capitalize()

            profile = str(parsed.get("profile", "driving-car")).lower()
            if profile not in ("driving-car", "foot-walking"):
                profile = "driving-car"

            return_to_start = bool(parsed.get("return_to_start", False))
            max_stops = parsed.get("max_stops")
            if max_stops is not None:
                try:
                    max_stops = int(max_stops)
                    if max_stops < 1:
                        max_stops = None
                except (ValueError, TypeError):
                    max_stops = None

            return ParsedConstraints(
                start_monument=start,
                time_budget_minutes=budget,
                must_visit=must_visit,
                preferences=prefs,
                profile=profile,
                return_to_start=return_to_start,
                max_stops=max_stops,
            )
        except (RuntimeError, ValueError, KeyError, TypeError, json.JSONDecodeError, httpx.HTTPError) as exc:
            logger.info("Falling back to heuristic preference parser: %s", exc)
            return self._heuristic_parse(text)

    def _match_monument(self, text: str) -> str | None:
        """Match monument name to valid slug."""
        text_lower = text.lower()
        for kw, slug in MONUMENT_KEYWORDS.items():
            if kw in text_lower:
                return slug
        for slug in VALID_SLUGS:
            if slug.replace("-", " ") in text_lower or slug in text_lower:
                return slug
        return None

    def _heuristic_parse(self, text: str) -> ParsedConstraints:
        """Reliable rule-based parser for when Gemini is unconfigured or unavailable."""
        text_lower = text.lower()

        # Detect monuments
        found_slugs: list[str] = []
        for kw, slug in MONUMENT_KEYWORDS.items():
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower) and slug not in found_slugs:
                found_slugs.append(slug)

        start = found_slugs[0] if found_slugs else None
        must_visit = found_slugs[1:] if len(found_slugs) > 1 else []

        # Detect duration
        budget: float | None = None
        hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hour|hr|hrs|hours)\b", text_lower)
        min_match = re.search(r"(\d+)\s*(?:min|mins|minutes)\b", text_lower)
        if hour_match:
            budget = float(hour_match.group(1)) * 60.0
        elif min_match:
            budget = float(min_match.group(1))
        elif "half day" in text_lower:
            budget = 240.0
        elif "full day" in text_lower:
            budget = 480.0

        # Detect city
        prefs: dict[str, Any] = {}
        if "delhi" in text_lower:
            prefs["city"] = "Delhi"
        elif "agra" in text_lower:
            prefs["city"] = "Agra"

        # Detect profile
        profile = "foot-walking" if "walk" in text_lower or "foot" in text_lower else "driving-car"

        # Detect loop
        return_to_start = any(k in text_lower for k in ("round trip", "loop", "return to start", "back to start"))

        # Detect max stops
        max_stops: int | None = None
        stops_match = re.search(r"(?:max|at most|up to|limit of)\s*(\d+)\s*(?:stops|monuments|places)?", text_lower)
        if stops_match:
            max_stops = int(stops_match.group(1))

        return ParsedConstraints(
            start_monument=start,
            time_budget_minutes=budget,
            must_visit=must_visit,
            preferences=prefs,
            profile=profile,
            return_to_start=return_to_start,
            max_stops=max_stops,
        )

    def explain_itinerary(self, itinerary: Itinerary) -> str:
        """Generate a natural language narrative of the already-validated itinerary.

        Never alters or reorders stops; explains the exact schedule produced by the solver.
        """
        if not itinerary.is_feasible or not itinerary.stops:
            return (
                f"No feasible itinerary could be constructed: {itinerary.status_message} "
                f"(Solver status: {itinerary.solver_status}). Consider increasing your time budget "
                "or reducing the number of mandatory stops."
            )

        # Try Gemini API if available
        try:
            stops_summary = "\n".join(
                f"{i+1}. {s.name} ({s.monument_slug}) - Arrive: {s.arrival_time_min:.1f}m, "
                f"Visit: {s.visit_duration_min:.1f}m, Depart: {s.departure_time_min:.1f}m "
                f"(Travel to next: {s.travel_time_to_next_min:.1f}m, {s.travel_distance_to_next_m:.0f}m)"
                for i, s in enumerate(itinerary.stops)
            )
            prompt = (
                "You are an expert heritage tour guide for Raahein. "
                "Explain this pre-computed, solver-optimized itinerary to the visitor in an engaging, narrative style.\n"
                "CRITICAL RULES:\n"
                "1. You MUST NOT modify, reorder, add, or remove any stops.\n"
                "2. Keep the exact order of monuments given below.\n"
                "3. Explain why the sequence makes geographical and historical sense.\n\n"
                f"Total Duration: {itinerary.total_time_min:.1f} minutes\n"
                f"Total Distance: {itinerary.total_travel_distance_m / 1000.0:.1f} km\n"
                f"Profile: {itinerary.profile}\n"
                f"Itinerary stops:\n{stops_summary}\n\n"
                "Provide a concise, 2-3 paragraph tour overview and stop-by-stop journey."
            )
            return self._call_gemini(prompt)
        except (RuntimeError, ValueError, KeyError, TypeError, httpx.HTTPError) as exc:
            logger.info("Using fallback itinerary explanation generator: %s", exc)
            return self._fallback_explanation(itinerary)

    def _fallback_explanation(self, itinerary: Itinerary) -> str:
        """Deterministic, informative explanation when Gemini API is unavailable."""
        stop_names = [s.name for s in itinerary.stops]
        first_stop = stop_names[0]
        route_str = " -> ".join(stop_names)
        distance_km = itinerary.total_travel_distance_m / 1000.0
        hrs = int(itinerary.total_time_min // 60)
        mins = int(itinerary.total_time_min % 60)
        time_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"

        return (
            f"Your optimized tour begins at {first_stop} and visits {len(itinerary.stops)} monuments: "
            f"{route_str}. The complete itinerary covers {distance_km:.1f} km with a total duration of "
            f"{time_str} ({itinerary.total_travel_time_min:.1f} mins transit and "
            f"{itinerary.total_visit_time_min:.1f} mins monument exploration). "
            "Each stop is planned with sufficient visit time to explore key architectural highlights."
        )


def get_gemini_service() -> GeminiService:
    """FastAPI dependency for accessing GeminiService."""
    return GeminiService()
