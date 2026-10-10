from app.retrieval.fusion import deduplicate, merge_rank_map, rrf_fuse


def test_rrf_fuse_rewards_consensus():
    fused = rrf_fuse([[0, 1, 2], [1, 0, 3]], k=60)
    order = [idx for idx, _ in fused]
    assert order[0] in (0, 1)
    assert set(order) == {0, 1, 2, 3}
    scores = dict(fused)
    assert scores[0] > scores[2]
    assert scores[1] > scores[3]


def test_merge_rank_map_is_one_based():
    assert merge_rank_map([5, 2]) == {5: 1, 2: 2}


def test_deduplicate_removes_near_duplicates():
    texts = [
        "The Eiffel Tower is located in Paris France.",
        "The Eiffel Tower is located in Paris, France!",
        "Quantum computing uses qubits and quantum gates.",
    ]
    kept = deduplicate([0, 1, 2], texts, threshold=0.6)
    assert 0 in kept
    assert 1 not in kept
    assert 2 in kept
