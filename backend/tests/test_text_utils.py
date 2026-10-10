from app.core.text import (
    domain_of,
    entity_hints,
    has_negation,
    has_year,
    jaccard,
    looks_like_claim,
    normalize_whitespace,
    shingles,
    split_sentences,
)


def test_split_sentences_preserves_offsets():
    text = "Paris is the capital of France. It is on the Seine."
    sentences = split_sentences(text)
    assert [s.text for s in sentences] == [
        "Paris is the capital of France.",
        "It is on the Seine.",
    ]
    for sentence in sentences:
        assert text[sentence.start : sentence.end] == sentence.text


def test_title_abbreviation_does_not_split():
    sentences = split_sentences("Dr. Smith works at the lab. He publishes often.")
    assert len(sentences) == 2
    assert sentences[0].text.startswith("Dr. Smith")


def test_decimal_is_not_a_sentence_boundary():
    assert len(split_sentences("Pi is about 3.14 approximately.")) == 1


def test_looks_like_claim_filters_non_claims():
    assert looks_like_claim("The Eiffel Tower is located in Paris.")
    assert not looks_like_claim("Is the Eiffel Tower in Paris?")
    assert not looks_like_claim("I think this is great.")
    assert not looks_like_claim("Short.")


def test_shingles_and_jaccard():
    first = shingles("the quick brown fox jumps over the lazy dog")
    same = shingles("the quick brown fox jumps over the lazy dog")
    other = shingles("a completely different sentence about something else entirely")
    assert jaccard(first, same) == 1.0
    assert jaccard(first, other) < 0.2


def test_entity_hints_negation_and_year():
    hints = entity_hints("The Eiffel Tower is located in Paris")
    assert "Eiffel Tower" in hints
    assert has_negation("The wall is not in Japan")
    assert has_year("It was released in 1991")
    assert not has_year("It was released recently")


def test_normalize_whitespace_and_domain():
    assert normalize_whitespace("  a   b\n c ") == "a b c"
    assert domain_of("https://en.wikipedia.org/wiki/Paris") == "en.wikipedia.org"
