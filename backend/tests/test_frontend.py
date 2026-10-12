from app.main import create_app
from fastapi.testclient import TestClient


def test_index_serves_the_expected_ui_contract():
    with TestClient(create_app()) as client:
        response = client.get("/")
    assert response.status_code == 200
    html = response.text
    for element_id in ('id="analyze-form"', 'id="text-input"', 'id="url-input"', 'id="status-region"'):
        assert element_id in html
    assert "/app.js" in html
    assert "/styles.css" in html


def test_static_assets_are_served_and_call_the_api():
    with TestClient(create_app()) as client:
        app_js = client.get("/app.js")
        styles = client.get("/styles.css")
    assert app_js.status_code == 200
    assert styles.status_code == 200
    # The frontend must talk to the versioned API and know every backend status.
    for status in (
        "SUPPORTED",
        "REFUTED",
        "CONFLICTING_EVIDENCE",
        "INSUFFICIENT_EVIDENCE",
        "UNABLE_TO_ASSESS",
        "NOT_VERIFIABLE",
    ):
        assert status in app_js.text
    assert "/api/analyze" in app_js.text
    # NOT_VERIFIABLE is labelled by claim type, not blanket-called an opinion.
    for claim_type in ("OPINION_SUBJECTIVE", "PREDICTION", "ALLEGATION", "UNCLEAR"):
        assert claim_type in app_js.text
    assert "Opinion / not directly verifiable" not in app_js.text
