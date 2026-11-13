import math

import pytest

from app.retrieval.bm25 import BM25, PATTERN_1, PATTERN_2, PATTERN_3, tokenize


def chunk(source: str, index: int, text: str) -> dict:
    return {"source": source, "chunk_index": index, "chunk": text}


CHUNKS = [
    chunk("a.md", 0, "Fare code FARE-K is non-changeable."),
    chunk("a.md", 1, "Cabin baggage allowance is seven kg for the main bag."),
    chunk("b.md", 0, "Checked baggage allowance depends on the journey."),
    chunk("b.md", 1, "A cancellation fee of INR 2,000 applies."),
]


def test_tokenize_lowercases_and_drops_punctuation() -> None:
    assert tokenize("Cabin bag: 7 kg, 55 x 35 cm.", PATTERN_1) == [
        "cabin", "bag", "7", "kg", "55", "x", "35", "cm",
    ]


def test_hyphen_handling_differs_between_patterns() -> None:
    assert tokenize("FARE-K", PATTERN_1) == ["fare", "k"]
    assert tokenize("FARE-K", PATTERN_2) == ["fare-k"]


def test_pattern_3_keeps_comma_grouped_numbers_whole() -> None:
    assert tokenize("INR 2,000 fee", PATTERN_2) == ["inr", "2", "000", "fee"]
    assert tokenize("INR 2,000 fee", PATTERN_3) == ["inr", "2,000", "fee"]


def test_tokenize_empty_text_returns_empty_list() -> None:
    assert tokenize("", PATTERN_2) == []


def test_index_statistics() -> None:
    bm25 = BM25(CHUNKS)

    assert bm25.N == 4
    assert set(bm25.index) == {"a.md:0", "a.md:1", "b.md:0", "b.md:1"}
    assert bm25.doc_freq["baggage"] == 2
    assert bm25.avg_len == sum(c["length"] for c in bm25.index.values()) / 4


def test_term_repeated_in_one_chunk_counts_once_in_doc_freq() -> None:
    bm25 = BM25([chunk("a.md", 0, "fee fee fee"), chunk("a.md", 1, "other")])

    assert bm25.doc_freq["fee"] == 1


def test_idf_matches_formula_and_rare_terms_weigh_more() -> None:
    bm25 = BM25(CHUNKS)

    assert bm25.idf("baggage") == pytest.approx(math.log(1 + (4 - 2 + 0.5) / (2 + 0.5)))
    assert bm25.idf("fare-k") > bm25.idf("baggage")
    assert bm25.idf("not-in-corpus") == 0.0


def test_search_returns_exact_code_match_only() -> None:
    results = BM25(CHUNKS).search("FARE-K")

    assert [chunk_id for chunk_id, _ in results] == ["a.md:0"]


def test_search_ranks_better_match_first_and_sorts_descending() -> None:
    results = BM25(CHUNKS).search("cabin baggage allowance", top_k=5)
    scores = [score for _, score in results]

    assert results[0][0] == "a.md:1"
    assert scores == sorted(scores, reverse=True)
    assert all(score > 0 for score in scores)


def test_search_respects_top_k() -> None:
    assert len(BM25(CHUNKS).search("baggage allowance", top_k=1)) == 1


def test_search_with_no_matching_terms_returns_nothing() -> None:
    assert BM25(CHUNKS).search("zebra giraffe") == []


def test_search_with_empty_query_or_empty_index_returns_nothing() -> None:
    assert BM25(CHUNKS).search("") == []
    assert BM25([]).search("baggage") == []


def test_query_uses_same_tokenizer_as_index() -> None:
    chunks = [chunk("a.md", 0, "Fee is INR 2,000."), chunk("a.md", 1, "Fee is INR 2,500.")]

    results = BM25(chunks, pattern=PATTERN_3).search("INR 2,000")

    assert results[0][0] == "a.md:0"
