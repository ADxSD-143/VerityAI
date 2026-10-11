import logging

import app.services.analyzer as analyzer_module
from app.main import create_app
from conftest import FakeAdapter, FakeNLI, fake_retrieve_factory, make_passage, score
from fastapi.testclient import TestClient

SECRET_CLAIM = "The classified codeword is BLUEHERON and it must never be logged."


def _patched_client(monkeypatch, passages, scores):
    application = create_app()
    analyzer = application.state.analyzer
    analyzer.adapters = [FakeAdapter(passages)]
    monkeypatch.setattr(analyzer_module, "retrieve", fake_retrieve_factory())
    analyzer._nli = FakeNLI(scores)
    return TestClient(application)


def test_claim_text_is_not_written_to_logs(monkeypatch, caplog):
    passages = [make_passage("Paris is the capital of France.", url="https://a.test/1")]
    with caplog.at_level(logging.DEBUG):
        with _patched_client(monkeypatch, passages, [score("entailment", 0.9)]) as client:
            response = client.post("/api/analyze", json={"claim": SECRET_CLAIM})
    assert response.status_code == 200
    assert all("BLUEHERON" not in record.getMessage() for record in caplog.records)
    assert all(SECRET_CLAIM not in record.getMessage() for record in caplog.records)


def test_validation_error_does_not_echo_user_input():
    with TestClient(create_app()) as client:
        response = client.post("/api/analyze", json={"claim": SECRET_CLAIM, "text": SECRET_CLAIM})
    assert response.status_code == 422
    assert "BLUEHERON" not in response.text
