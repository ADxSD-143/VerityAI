from app.analysis.independence import cluster_passages, document_key
from app.sources.base import EvidencePassage


def _passage(**kwargs) -> EvidencePassage:
    base = dict(text="x", source="wikipedia", title="T", url="https://a.test/1", publisher="a.test")
    base.update(kwargs)
    return EvidencePassage(**base)


def test_same_document_is_one_group():
    keys = ["https://a.test/x", "https://a.test/x"]
    texts = ["Paris is the capital of France.", "Entirely different text about Berlin."]
    groups = cluster_passages(texts, keys)
    assert groups[0] == groups[1]


def test_near_duplicate_text_across_documents_merges():
    sentence = "The report says the bridge opened in 1932 after four years of construction."
    groups = cluster_passages([sentence, sentence], ["https://a.test/1", "https://b.test/2"])
    assert groups[0] == groups[1]


def test_distinct_passages_are_independent():
    groups = cluster_passages(
        ["Paris is the capital of France.", "Quantum computing uses qubits and gates."],
        ["https://a.test/1", "https://b.test/2"],
    )
    assert groups[0] != groups[1]


def test_document_key_prefers_page_id_then_url():
    assert document_key(_passage(page_id="123")) == "wikipedia:123"
    assert document_key(_passage(page_id=None, url="https://a.test/1#frag")) == "https://a.test/1"
