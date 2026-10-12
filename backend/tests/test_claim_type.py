from app.services.claim_type import (
    ALLEGATION,
    CHECKABLE_FACT,
    OPINION_SUBJECTIVE,
    PREDICTION,
    UNCLEAR,
    classify_claim_type,
)


def test_checkable_facts_are_classified_as_facts():
    assert classify_claim_type("The Eiffel Tower is located in Paris.") == CHECKABLE_FACT
    assert classify_claim_type("Water is composed of hydrogen and oxygen.") == CHECKABLE_FACT
    assert classify_claim_type("World War II ended in 1945.") == CHECKABLE_FACT


def test_subjective_opinions():
    assert classify_claim_type("Chocolate is the best ice cream flavor.") == OPINION_SUBJECTIVE
    assert classify_claim_type("Mumbai is the greatest city in the world.") == OPINION_SUBJECTIVE
    assert classify_claim_type("That actor is the hottest person alive.") == OPINION_SUBJECTIVE


def test_predictions():
    assert classify_claim_type("Bitcoin will reach one million dollars by 2030.") == PREDICTION
    assert classify_claim_type("The sea level will rise by one metre by 2100.") == PREDICTION


def test_hindi_and_hinglish_superlatives_are_opinions():
    assert classify_claim_type("Modi sabse best PM hai.") == OPINION_SUBJECTIVE
    assert classify_claim_type("यह सबसे अच्छा विकल्प है।") == OPINION_SUBJECTIVE


def test_hindi_and_hinglish_first_person_opinions():
    assert classify_claim_type("Mujhe lagta hai ki yeh sahi hai.") == OPINION_SUBJECTIVE
    assert classify_claim_type("मेरे ख्याल से यह सही है।") == OPINION_SUBJECTIVE


def test_hindi_and_hinglish_predictions():
    assert classify_claim_type("Modi agle saal phir PM honge.") == PREDICTION
    assert classify_claim_type("Baarish kal hogi.") == PREDICTION
    assert classify_claim_type("भारत अगले साल विकासशील रहेगा।") == PREDICTION


def test_hindi_and_hinglish_allegations():
    assert classify_claim_type("Mantri par bhrashtachar ka aarop laga.") == ALLEGATION
    assert classify_claim_type("Neta par ilzaam lagaya gaya.") == ALLEGATION
    assert classify_claim_type("मंत्री पर भ्रष्टाचार का आरोप लगा।") == ALLEGATION


def test_allegations():
    assert classify_claim_type("The minister was accused of corruption in 2019.") == ALLEGATION
    assert classify_claim_type("A company executive was charged with fraud last year.") == ALLEGATION
    assert classify_claim_type("A celebrity was rumoured to have evaded taxes.") == ALLEGATION


def test_unclear_statements():
    assert classify_claim_type("Things are getting worse.") == UNCLEAR
    assert classify_claim_type("Everyone knows that.") == UNCLEAR
    assert classify_claim_type("short") == UNCLEAR


def test_pronoun_initial_factual_sentences_are_checkable():
    # A leading it/this/that/they does not make a concrete sentence non-verifiable.
    assert classify_claim_type("It was completed in 1889 and stands 330 metres tall.") == CHECKABLE_FACT
    assert classify_claim_type("This tower is located in Paris.") == CHECKABLE_FACT
    assert classify_claim_type("They built the bridge in 1889.") == CHECKABLE_FACT
    assert classify_claim_type("That building was designed by Gustave Eiffel.") == CHECKABLE_FACT
