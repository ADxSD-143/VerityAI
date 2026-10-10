import app.retrieval.pipeline as pipeline
from app.config import Settings
from app.core.errors import ModelLoadError
from conftest import make_passage


class _FakeRanker:
    def __init__(self, order):
        self._order = order

    def rank(self, query, k):
        return [(idx, 1.0 / (pos + 1)) for pos, idx in enumerate(self._order[:k])]


def _patch(monkeypatch, mode, bm25_order, dense_order=None, dense_error=False):
    monkeypatch.setattr(
        pipeline, "get_settings",
        lambda: Settings(verity_retrieval_mode=mode, verity_preload_models=False),
    )
    monkeypatch.setattr(pipeline, "BM25Index", lambda texts: _FakeRanker(bm25_order))
    if dense_error:
        def _boom(*args, **kwargs):
            raise ModelLoadError("no dense model")
        monkeypatch.setattr(pipeline, "get_sentence_transformer", _boom)
    else:
        monkeypatch.setattr(pipeline, "get_sentence_transformer", lambda *a, **k: object())
        monkeypatch.setattr(
            pipeline, "DenseIndex",
            lambda texts, model, model_id, cache=None: _FakeRanker(dense_order),
        )


def _passages(n=3):
    return [make_passage(f"distinct passage number {i}", url=f"https://a.test/{i}") for i in range(n)]


def test_dense_mode_uses_dense_order(monkeypatch):
    _patch(monkeypatch, "dense", bm25_order=[0, 1, 2], dense_order=[2, 1, 0])
    outcome = pipeline.retrieve("claim", _passages(), top_k=3)
    assert [rp.index for rp in outcome.ranked] == [2, 1, 0]
    assert outcome.degraded is False


def test_hybrid_mode_fuses_both(monkeypatch):
    _patch(monkeypatch, "hybrid", bm25_order=[0, 1, 2], dense_order=[2, 1, 0])
    outcome = pipeline.retrieve("claim", _passages(), top_k=3)
    order = [rp.index for rp in outcome.ranked]
    assert sorted(order) == [0, 1, 2]
    assert order != [2, 1, 0]


def test_dense_mode_degrades_to_bm25_when_dense_unavailable(monkeypatch):
    _patch(monkeypatch, "dense", bm25_order=[0, 1, 2], dense_error=True)
    outcome = pipeline.retrieve("claim", _passages(), top_k=3)
    assert [rp.index for rp in outcome.ranked] == [0, 1, 2]
    assert outcome.degraded is True
