def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[str]:
    """Merge ranked ID lists; each list adds 1 / (k + rank) to an ID (rank starts at 1).

    Only ranks are used, so scores from different retrievers (cosine distance,
    BM25) never need to be normalised against each other. Ties keep the order in
    which the IDs were first seen.
    """
    scores: dict[str, float] = {}
    for ranked_ids in ranked_lists:
        for rank, chunk_id in enumerate(ranked_ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (k + rank)
    return sorted(scores, key=scores.__getitem__, reverse=True)
