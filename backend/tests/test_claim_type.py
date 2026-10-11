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


def test_allegations():
    assert classify_claim_type("The minister was accused of corruption in 2019.") == ALLEGATION
    assert classify_claim_type("A company executive was charged with fraud last year.") == ALLEGATION
    assert classify_claim_type("A celebrity was rumoured to have evaded taxes.") == ALLEGATION


def test_unclear_statements():
    assert classify_claim_type("Things are getting worse.") == UNCLEAR
    assert classify_claim_type("Everyone knows that.") == UNCLEAR
    assert classify_claim_type("short") == UNCLEAR
