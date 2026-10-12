from app.services.claim_extraction import extract_claims, query_variants, single_claim


def test_extract_claims_filters_and_keeps_offsets():
    text = (
        "The Eiffel Tower is located in Paris. Is it tall? I think it is nice. "
        "It was completed in 1889 and stands 330 metres tall."
    )
    claims = extract_claims(text, max_claims=5)
    texts = [claim.text for claim in claims]
    assert any("Eiffel Tower" in t for t in texts)
    assert any("1889" in t for t in texts)
    assert not any(t.endswith("?") for t in texts)
    assert not any("I think" in t for t in texts)
    for claim in claims:
        assert text[claim.start : claim.end] == claim.text


def test_extract_claims_segments_roman_hinglish():
    text = (
        "Bharat ki rajdhani New Delhi hai. Taj Mahal Agra mein sthit hai. "
        "Yeh film bahut acchi thi."
    )
    claims = extract_claims(text, max_claims=10)
    assert len(claims) == 3
    assert "New Delhi hai" in claims[0].text
    assert "Taj Mahal" in claims[1].text
    for claim in claims:
        assert text[claim.start : claim.end] == claim.text


def test_extract_claims_segments_devanagari_on_danda():
    text = "भारत की राजधानी नई दिल्ली है। ताजमहल आगरा में स्थित है। मुंबई बड़ा शहर है।"
    claims = extract_claims(text, max_claims=10)
    assert len(claims) == 3
    for claim in claims:
        assert text[claim.start : claim.end] == claim.text


def test_extract_claims_falls_back_to_whole_text():
    claims = extract_claims("no", max_claims=5)
    assert len(claims) == 1
    assert claims[0].notes


def test_single_claim_preserves_wording():
    claims = single_claim("  The Great   Wall is in China.  ")
    assert claims[0].text == "The Great Wall is in China."
    assert claims[0].source == "input"


def test_query_variants_include_entity_variant():
    variants = query_variants("The Eiffel Tower is located in Paris.")
    assert variants[0] == "The Eiffel Tower is located in Paris."
    assert any("Eiffel Tower" in v for v in variants)
