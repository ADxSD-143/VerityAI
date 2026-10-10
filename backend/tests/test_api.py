import app.services.analyzer as analyzer_module
from app.main import create_app
from conftest import FakeAdapter, FakeNLI, fake_retrieve_factory, make_passage, score
from fastapi.testclient import TestClient


def _patched_client(monkeypatch, passages, scores):
    application = create_app()
    analyzer = application.state.analyzer
    analyzer.adapters = [FakeAdapter(passages)]
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())
    analyzer._nli = FakeNLI(scores)
    return TestClient(application)


def test_health_endpoint():
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert isinstance(body["models_loaded"], list)


def test_frontend_is_served():
    with TestClient(create_app()) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "VerityAI" in response.text


def test_analyze_requires_exactly_one_input():
    with TestClient(create_app()) as client:
        empty = client.post("/api/analyze", json={})
        both = client.post("/api/analyze", json={"claim": "x", "text": "y"})
    assert empty.status_code == 422
    assert both.status_code == 422
    assert both.json()["code"] == "invalid_input"


def test_analyze_success(monkeypatch):
    passages = [make_passage("Paris is the capital of France.", url="https://a.test/1")]
    with _patched_client(monkeypatch, passages, [score("entailment", 0.95)]) as client:
        response = client.post("/api/analyze", json={"claim": "Paris is the capital of France."})
    assert response.status_code == 200
    body = response.json()
    assert body["claims"][0]["status"] == "SUPPORTED"
    assert body["sources_queried"][0]["source"] == "fake"
    assert body["meta"]["analysis_id"]


def test_analyze_url_rejects_unsafe_scheme():
    with TestClient(create_app()) as client:
        response = client.post("/api/analyze-url", json={"url": "ftp://example.com/file"})
    assert response.status_code == 400
    assert response.json()["code"] == "unsafe_url"
