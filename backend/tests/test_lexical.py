from app.retrieval.lexical import BM25Index


def test_bm25_ranks_relevant_document_first():
    docs = [
        "Paris is the capital of France.",
        "Berlin is the capital of Germany.",
        "The Seine flows through Paris.",
    ]
    ranked = BM25Index(docs).rank("capital of Germany", top_k=3)
    assert ranked
    assert ranked[0][0] == 1


def test_bm25_handles_empty_corpus_and_query():
    assert BM25Index([]).rank("anything", top_k=5) == []
    ranked = BM25Index(["Paris is the capital of France."]).rank("", top_k=5)
    assert ranked == []
