import pytest

from app.retrieval.fusion import reciprocal_rank_fusion


def test_chunk_ranked_well_by_both_lists_wins() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"]])

    assert fused[:2] == ["a", "b"]  # tie on score, a was seen first
    assert set(fused) == {"a", "b", "c", "d"}


def test_agreement_beats_a_single_first_place() -> None:
    fused = reciprocal_rank_fusion([["x", "shared"], ["y", "shared"]])

    assert fused[0] == "shared"


def test_scores_follow_the_formula() -> None:
    fused = reciprocal_rank_fusion([["a"], ["b", "a"]], k=60)

    # a: 1/61 + 1/62, b: 1/61 -> a first
    assert fused == ["a", "b"]
    assert 1 / 61 + 1 / 62 > 1 / 61


def test_chunk_in_only_one_list_is_kept() -> None:
    assert reciprocal_rank_fusion([["a"], []]) == ["a"]


def test_empty_inputs_return_empty_list() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


def test_ties_keep_first_seen_order() -> None:
    assert reciprocal_rank_fusion([["a", "b"], ["c"]]) == ["a", "c", "b"]


@pytest.mark.parametrize("k", [1, 60])
def test_single_list_keeps_its_order(k: int) -> None:
    assert reciprocal_rank_fusion([["a", "b", "c"]], k=k) == ["a", "b", "c"]
