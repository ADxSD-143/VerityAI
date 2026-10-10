import asyncio

from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_analysis_timeout_returns_typed_504():
    app = create_app(
        Settings(verity_preload_models=False, verity_analysis_timeout_s=0.01)
    )

    async def slow_analysis(payload):
        await asyncio.sleep(0.1)
        raise AssertionError("Timed out analysis should not reach this line.")

    app.state.analyzer.analyze = slow_analysis
    with TestClient(app) as client:
        response = client.post("/api/analyze", json={"claim": "test claim"})

    assert response.status_code == 504
    assert response.json()["code"] == "analysis_timeout"
    assert response.json()["details"]["timeout_s"] == 0.01
