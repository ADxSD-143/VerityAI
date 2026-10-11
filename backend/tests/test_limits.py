from app.config import Settings
from app.core.limits import RequestLimitsMiddleware
from app.main import create_app
from fastapi.testclient import TestClient


async def _ok_app(scope, receive, send):  # noqa: ANN001
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def _scope(ip: str, path: str = "/api/analyze") -> dict:
    return {"type": "http", "path": path, "client": (ip, 1234), "headers": []}


async def _call(middleware, ip: str, path: str = "/api/analyze") -> int:
    captured: dict = {}

    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

    async def send(message):
        captured[message["type"]] = message

    await middleware(_scope(ip, path), receive, send)
    return captured["http.response.start"]["status"]


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


async def test_rate_limiter_is_per_client():
    middleware = RequestLimitsMiddleware(_ok_app, max_requests=1, window_s=60)
    assert await _call(middleware, "10.0.0.1") == 200
    assert await _call(middleware, "10.0.0.1") == 429
    assert await _call(middleware, "10.0.0.2") == 200  # independent client


async def test_rate_limiter_ignores_unprotected_paths():
    middleware = RequestLimitsMiddleware(_ok_app, max_requests=1, window_s=60)
    assert await _call(middleware, "10.0.0.3") == 200
    assert await _call(middleware, "10.0.0.3") == 429
    # /health is not a protected path, so it is never rate limited.
    assert await _call(middleware, "10.0.0.3", path="/health") == 200
