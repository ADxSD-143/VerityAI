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


@pytest.mark.parametrize(
    ("model_id", "id2label", "expected"),
    [
        (
            "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli",
            {0: "entailment", 1: "neutral", 2: "contradiction"},
            {0: "entailment", 1: "neutral", 2: "contradiction"},
        ),
        (
            "cross-encoder/nli-deberta-v3-small",
            {0: "contradiction", 1: "entailment", 2: "neutral"},
            {0: "contradiction", 1: "entailment", 2: "neutral"},
        ),
    ],
)
def test_candidate_model_label_maps_are_resolved_from_config(model_id, id2label, expected):
    assert model_id
    assert NLIModel._resolve_label_map(_Config(id2label)) == expected


def test_label_map_rejects_unresolvable_labels():
    with pytest.raises(ValueError):
        NLIModel._resolve_label_map(_Config({0: "LABEL_0", 1: "LABEL_1", 2: "LABEL_2"}))


def test_label_map_requires_three_classes():
    with pytest.raises(ValueError):
        NLIModel._resolve_label_map(_Config({0: "entailment", 1: "neutral"}))
