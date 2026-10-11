from app.services.allegation import summarize_allegation


def test_official_finding_language_is_flagged():
    established, notes = summarize_allegation(["The executive was convicted of fraud in 2019."])
    assert established is True
    assert any("official-finding" in note for note in notes)


def test_allegation_framing_without_a_finding():
    established, notes = summarize_allegation(["A minister was accused of corruption in 2019."])
    assert established is False
    assert any("refer to the allegation itself" in note for note in notes)


def test_no_markers_reports_no_finding():
    established, notes = summarize_allegation(["Paris is the capital of France."])
    assert established is False
    assert any("No official finding" in note for note in notes)
