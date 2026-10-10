from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_analysis_endpoints_are_rate_limited_per_client():
    app = create_app(
        Settings(
            verity_preload_models=False,
            verity_rate_limit_requests=2,
            verity_rate_limit_window_s=60,
        )
    )
    with TestClient(app) as client:
        first = client.post("/api/analyze", json={})
        second = client.post("/api/analyze-url", json={"url": "ftp://example.com"})
        third = client.post("/api/analyze", json={})
        health = client.get("/health")

    assert first.status_code == 422
    assert second.status_code == 400
    assert third.status_code == 429
    assert third.json()["code"] == "rate_limited"
    assert int(third.headers["retry-after"]) >= 1
    assert health.status_code == 200


def test_analysis_request_body_size_is_capped():
    app = create_app(
        Settings(verity_preload_models=False, verity_max_request_bytes=1024)
    )
    with TestClient(app) as client:
        response = client.post("/api/analyze", json={"claim": "x" * 2000})

    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"
