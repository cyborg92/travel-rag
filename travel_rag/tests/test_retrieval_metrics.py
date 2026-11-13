import pytest

from app.retrieval.retrieval_metrics import aggregate_metrics, retrieval_metrics

NONE_METRICS = {
    "hit_at_k": None,
    "precision_at_k": None,
    "recall_at_k": None,
    "reciprocal_rank": None,
}


def test_hit_with_expected_chunk_ranked_first():
    result = retrieval_metrics(["a"], ["a", "x", "y"], k=3)

    assert result == {
        "hit_at_k": 1.0,
        "precision_at_k": pytest.approx(1 / 3),
        "recall_at_k": 1.0,
        "reciprocal_rank": 1.0,
    }


def test_expected_chunk_ranked_second_halves_reciprocal_rank():
    result = retrieval_metrics(["a"], ["x", "a", "y"], k=3)

    assert result["reciprocal_rank"] == 0.5


def test_miss_scores_zero_everywhere():
    result = retrieval_metrics(["a"], ["x", "y", "z"], k=3)

    assert result == {
        "hit_at_k": 0.0,
        "precision_at_k": 0.0,
        "recall_at_k": 0.0,
        "reciprocal_rank": 0.0,
    }


def test_multi_chunk_partial_retrieval_hits_but_recall_is_half():
    result = retrieval_metrics(["a", "b"], ["a", "x", "y"], k=3)

    assert result["hit_at_k"] == 1.0
    assert result["recall_at_k"] == 0.5


def test_chunk_beyond_k_is_ignored():
    result = retrieval_metrics(["a"], ["x", "y", "a"], k=2)

    assert result["hit_at_k"] == 0.0
    assert result["reciprocal_rank"] == 0.0


def test_fewer_retrieved_than_k_still_divides_precision_by_k():
    result = retrieval_metrics(["a"], ["a"], k=3)

    assert result["precision_at_k"] == pytest.approx(1 / 3)


def test_unanswerable_case_returns_none_metrics():
    assert retrieval_metrics([], ["x", "y", "z"], k=3) == NONE_METRICS


@pytest.mark.parametrize("k", [0, -1])
def test_non_positive_k_is_rejected(k):
    with pytest.raises(ValueError):
        retrieval_metrics(["a"], ["a"], k=k)


def test_aggregate_skips_unanswerable_cases():
    per_case = [
        {"hit_at_k": 1.0, "precision_at_k": 1 / 3, "recall_at_k": 1.0, "reciprocal_rank": 0.5},
        {"hit_at_k": 1.0, "precision_at_k": 1 / 3, "recall_at_k": 1.0, "reciprocal_rank": 1.0},
        {"hit_at_k": 1.0, "precision_at_k": 1 / 3, "recall_at_k": 0.5, "reciprocal_rank": 1.0},
        {"hit_at_k": 1.0, "precision_at_k": 1 / 3, "recall_at_k": 1.0, "reciprocal_rank": 1.0},
        NONE_METRICS,
    ]

    result = aggregate_metrics(per_case)

    assert result["hit_at_k_avg"] == 1.0
    assert result["precision_at_k_avg"] == pytest.approx(1 / 3)
    assert result["recall_at_k_avg"] == 0.875
    assert result["mrr"] == 0.875


def test_aggregate_with_only_unanswerable_cases_returns_none():
    assert aggregate_metrics([NONE_METRICS]) == {
        "hit_at_k_avg": None,
        "precision_at_k_avg": None,
        "recall_at_k_avg": None,
        "mrr": None,
    }


def test_aggregate_with_no_cases_returns_none():
    assert aggregate_metrics([])["mrr"] is None
