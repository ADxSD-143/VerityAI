import pytest
from app.analysis.nli import NLIModel, canonicalize_label


class _Config:
    def __init__(self, id2label):
        self.id2label = id2label


def test_canonicalize_label_variants():
    assert canonicalize_label("ENTAILMENT") == "entailment"
    assert canonicalize_label("contradiction") == "contradiction"
    assert canonicalize_label("Neutral") == "neutral"
    assert canonicalize_label("label_0") is None


def test_label_map_read_from_config():
    mapping = NLIModel._resolve_label_map(
        _Config({0: "entailment", 1: "neutral", 2: "contradiction"})
    )
    assert mapping == {0: "entailment", 1: "neutral", 2: "contradiction"}


def test_label_map_rejects_unresolvable_labels():
    with pytest.raises(ValueError):
        NLIModel._resolve_label_map(_Config({0: "LABEL_0", 1: "LABEL_1", 2: "LABEL_2"}))


def test_label_map_requires_three_classes():
    with pytest.raises(ValueError):
        NLIModel._resolve_label_map(_Config({0: "entailment", 1: "neutral"}))
