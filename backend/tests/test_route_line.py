import json
from unittest.mock import MagicMock, patch

import pytest

from app.planner import route_line as module
from app.planner.route_line import route_line

A, B, C = (28.60, 77.20), (28.61, 77.21), (28.62, 77.22)


def _response(payload: bytes) -> MagicMock:
    response = MagicMock()
    response.read.return_value = payload
    response.__enter__.return_value = response
    return response


def _osrm(*legs) -> bytes:
    return json.dumps({"code": "Ok", "routes": [{"legs": [
        {"steps": [{"geometry": {"coordinates": [[lng, lat] for lat, lng in leg]}}]} for leg in legs
    ]}]}).encode()


@pytest.fixture(autouse=True)
def _empty_cache():
    module._road_legs.cache_clear()


def test_uses_real_road_shapes_for_each_leg():
    bend = (28.605, 77.215)
    with patch("urllib.request.urlopen", return_value=_response(_osrm([A, bend, B], [B, C]))):
        line = route_line("driving-car", [A, B, C])
    assert line["source"] == "roads"
    assert line["legs"] == [[list(A), list(bend), list(B)], [list(B), list(C)]]


@pytest.mark.parametrize("failure", [
    {"side_effect": OSError("offline")},
    {"side_effect": TimeoutError()},
    {"return_value": _response(b"<html>overloaded</html>")},
    {"return_value": _response(b'{"code": "NoRoute"}')},
    {"return_value": _response(b'{"code": "Ok", "routes": [{"legs": [{}]}]}')},
    {"return_value": _response(_osrm([A, B]))},  # one leg back for two requested
])
def test_falls_back_to_straight_lines_and_never_raises(failure):
    with patch("urllib.request.urlopen", **failure):
        line = route_line("foot-walking", [A, B, C])
    assert line == {"source": "straight", "legs": [[list(A), list(B)], [list(B), list(C)]]}


def test_a_failure_is_not_cached_but_a_success_is():
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        assert route_line("driving-car", [A, B])["source"] == "straight"
    with patch("urllib.request.urlopen", return_value=_response(_osrm([A, B]))) as opened:
        assert route_line("driving-car", [A, B])["source"] == "roads"
        assert route_line("driving-car", [A, B])["source"] == "roads"
    assert opened.call_count == 1
