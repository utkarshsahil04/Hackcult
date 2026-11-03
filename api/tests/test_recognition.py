import io
import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")

import pytest
from app.main import app
from app.ml import (
    Candidate,
    PipelineResult,
    PipelineStatus,
    RecognitionPipeline,
    get_pipeline,
)
from app.routes.recognition import _rate_store
from fastapi.testclient import TestClient

# -- Minimal valid JPEG bytes (SOI marker only) --------------------------------
JPEG = b"\xff\xd8" + b"\x00" * 10
PNG  = b"\x89PNG" + b"\x00" * 10


# -- Pipeline stubs ------------------------------------------------------------
class _OkPipeline(RecognitionPipeline):
    def status(self):
        return PipelineStatus(models="ok", faiss_index="ok")

    def _run(self, image_bytes):
        return PipelineResult(
            status="ok",
            candidates=[
                Candidate(slug="qutub-minar", name="Qutub Minar", score=0.91),
                Candidate(slug="iron-pillar", name="Iron Pillar", score=0.74),
                Candidate(slug="iltutmish-tomb", name="Iltutmish Tomb", score=0.61),
            ],
        )


class _UncertainPipeline(RecognitionPipeline):
    def _run(self, image_bytes):
        return PipelineResult(status="uncertain", candidates=[])


class _BrokenPipeline(RecognitionPipeline):
    def _run(self, image_bytes):
        raise RuntimeError("GPU exploded")

class _ErrorResultPipeline(RecognitionPipeline):
    def _run(self, image_bytes):
        return PipelineResult(status="error", candidates=[], error="Model unavailable")

# -- Fixtures ------------------------------------------------------------------
def _make_client(pipeline_instance):

    from app.main import app as _app
    _app.dependency_overrides[get_pipeline] = lambda: pipeline_instance
    client = TestClient(_app, raise_server_exceptions=False)
    return client, _app


@pytest.fixture
def ok_client():
    _inst = _OkPipeline()
    app.dependency_overrides[get_pipeline] = lambda: _inst
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(get_pipeline, None)


@pytest.fixture
def uncertain_client():
    _inst = _UncertainPipeline()
    app.dependency_overrides[get_pipeline] = lambda: _inst
    client = TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(get_pipeline, None)  # restore before yielding
    app.dependency_overrides[get_pipeline] = lambda: _inst  # re-bind to instance
    yield client
    app.dependency_overrides.pop(get_pipeline, None)


@pytest.fixture
def broken_client():
    _inst = _BrokenPipeline()
    app.dependency_overrides[get_pipeline] = lambda: _inst
    client = TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(get_pipeline, None)
    app.dependency_overrides[get_pipeline] = lambda: _inst
    yield client
    app.dependency_overrides.pop(get_pipeline, None)


# -- Helpers -------------------------------------------------------------------
def _post(client, data=JPEG, mime="image/jpeg", field="photo"):
    return client.post(
        "/api/recognition/identify",
        files={field: ("photo.jpg", io.BytesIO(data), mime)},
    )


# -- Tests ---------------------------------------------------------------------
def test_ok_returns_200_with_candidates(ok_client):
    r = _post(ok_client)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert len(body["candidates"]) == 3
    first = body["candidates"][0]
    assert first["slug"] == "qutub-minar"
    assert 0.0 <= first["score"] <= 1.0


def test_uncertain_returns_200_not_500(uncertain_client):
    r = _post(uncertain_client)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "uncertain"
    assert body["candidates"] == []


def test_model_failure_returns_500_envelope(broken_client):
    r = _post(broken_client)
    assert r.status_code == 500
    err = r.json()["error"]
    assert err["code"] == "RECOGNITION_ERROR"
    assert err["message"]
    assert err["hint"]

def test_pipeline_error_status_returns_500_envelope():
    instance = _ErrorResultPipeline()
    client, test_app = _make_client(instance)
    try:
        response = _post(client)
        assert response.status_code == 500
        err = response.json()["error"]
        assert err["code"] == "RECOGNITION_ERROR"
        assert err["message"]
        assert err["hint"]
    finally:
        test_app.dependency_overrides.pop(get_pipeline, None)


def test_uncertain_and_broken_look_different():
    u_inst = _UncertainPipeline()
    app.dependency_overrides[get_pipeline] = lambda: u_inst
    u = _post(TestClient(app, raise_server_exceptions=False))

    b_inst = _BrokenPipeline()
    app.dependency_overrides[get_pipeline] = lambda: b_inst
    b = _post(TestClient(app, raise_server_exceptions=False))

    app.dependency_overrides.pop(get_pipeline, None)
    assert u.status_code == 200
    assert b.status_code == 500


def test_non_image_rejected_with_400(ok_client):
    r = _post(ok_client, data=b"not an image", mime="application/pdf")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_wrong_magic_bytes_rejected(ok_client):
    r = _post(ok_client, data=b"\x00\x00\x00\x00" + b"x" * 100, mime="image/jpeg")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_oversized_upload_rejected(ok_client):
    big = JPEG + b"\x00" * (6 * 1024 * 1024)
    r = _post(ok_client, data=big)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "UPLOAD_TOO_LARGE"


def test_png_accepted(ok_client):
    r = _post(ok_client, data=PNG, mime="image/png")
    assert r.status_code == 200


def test_health_reports_pipeline_status(ok_client):
    r = ok_client.get("/api/health")
    assert r.status_code == 200
    sub = r.json()["subsystems"]
    assert sub["models"] == "ok"
    assert sub["faiss_index"] == "ok"

def test_rate_limit_blocks_31st_request():
    instance = _OkPipeline()
    test_app = app
    test_app.dependency_overrides[get_pipeline] = lambda: instance
    test_ip = "192.0.2.123"
    client = TestClient(
        test_app,
        raise_server_exceptions=False,
        client=(test_ip, 50000),
    )

    try:
        for _ in range(30):
            response = client.post(
                "/api/recognition/identify",
                files={"photo": ("photo.jpg", io.BytesIO(JPEG), "image/jpeg")},
            )
            assert response.status_code == 200

        response = client.post(
            "/api/recognition/identify",
            files={"photo": ("photo.jpg", io.BytesIO(JPEG), "image/jpeg")},
        )
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "RATE_LIMITED"
    finally:
        _rate_store.pop(test_ip, None)
        test_app.dependency_overrides.pop(get_pipeline, None)
