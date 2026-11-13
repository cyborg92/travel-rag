"""
The shopping-list analogy

You send someone to the shop with a list: milk and eggs (these are your expected items).
They come back with a bag of 3 items: bread, eggs, soap (these are your retrieved items).

Overlap: only eggs matches, so the count is 1.

Now there are four different questions you can ask about that bag.

1. Hit: “Did I get anything useful at all?”
Rule: if the overlap is at least 1, the answer is 1. Otherwise it is 0.
Algorithm: loop through the bag and stop as soon as you find any item that is on the list.
Example: eggs is on the list, so Hit = 1.
Weakness: it is satisfied by one item, even if you needed five. That is how it hides a multi-chunk miss.

2. Precision: “How much of the bag is useful?”
Rule: overlap divided by the bag size.
Algorithm: count the items in the bag that are on the list, then divide by 3.
Example: 1 useful item out of 3 in the bag, so Precision = 1/3.
It tells you: how much noise came back with the good stuff.

3. Recall: “How much of the list did I get?”
Rule: the number of list items found, divided by the list size.
Algorithm: loop through the list (not the bag) and count how many items are in the bag, then divide by the list length.
Example: the list has 2 items (milk, eggs) and only eggs was found, so Recall = 1/2.
It tells you: whether you missed something you needed. This is the metric that catches a multi-chunk failure.

The difference between precision and recall is which side you divide by. Precision divides by what you got back. Recall divides by what you needed.

4. Reciprocal rank: “How early did the first useful item appear?”

This is the only one where order matters, so the bag is a ranked list, not a pile.

Rule: find the position of the first useful item (counting from 1), then compute 1 divided by that position. If nothing useful appears, the answer is 0.
Algorithm: walk through the list in order with a position counter. At the first item that is on the expected list, return 1/position and stop.
Example: [bread, eggs, soap]. Eggs is at position 2, so RR = 1/2.
Scale: first place gives 1.0, second gives 0.5, third gives 0.33, and not found gives 0.

It matters because the model reads the top chunks most closely, so a correct chunk ranked first is better than one ranked third.

(MRR is just the average of reciprocal rank across all your questions. The function computes one question is reciprocal rank. Averaging happens later, in the runner.)
"""

def retrieval_metrics(expected_chunks_ids: list[str], retrieved_chunks_ids: list[str], k: int) -> dict:
    if k <= 0:
        raise ValueError("k must be a positive integer")
    if not expected_chunks_ids:
        return {
            "hit_at_k": None,
            "precision_at_k": None,
            "recall_at_k": None,
            "reciprocal_rank": None,
        }

    return {
        "hit_at_k": hit_k_metric(expected_chunks_ids, retrieved_chunks_ids, k),
        "precision_at_k": precision_k_metric(expected_chunks_ids, retrieved_chunks_ids, k),
        "recall_at_k": recall_k_metric(expected_chunks_ids, retrieved_chunks_ids, k),
        "reciprocal_rank": reciprocal_rank(expected_chunks_ids, retrieved_chunks_ids, k),
    }


def hit_k_metric(expected_chunks_ids: list[str], retrieved_chunks_ids: list[str], k: int) ->float:
    for chunk in retrieved_chunks_ids[:k]:
        if chunk in expected_chunks_ids:
            return 1.0
    return 0.0


def precision_k_metric(expected_chunks_ids: list[str], retrieved_chunks_ids: list[str], k: int) ->float:
    count = 0
    for chunk in retrieved_chunks_ids[:k]:
        if chunk in expected_chunks_ids:
            count += 1
    return count / k


def recall_k_metric(expected_chunks_ids: list[str], retrieved_chunks_ids: list[str], k: int) ->float:
    top_k = retrieved_chunks_ids[:k]
    count = 0
    for chunk in expected_chunks_ids:
        if chunk in top_k:
            count += 1
    return count / len(expected_chunks_ids)


def reciprocal_rank(expected_chunks_ids: list[str], retrieved_chunks_ids: list[str], k: int) ->float:
    for position, chunk in enumerate(retrieved_chunks_ids[:k], start=1):
        if chunk in expected_chunks_ids:
            return 1 / position
    return 0.0


# Maps each per-case metric key to its name in the aggregate summary.
_AGGREGATE_KEYS = {
    "hit_at_k": "hit_at_k_avg",
    "precision_at_k": "precision_at_k_avg",
    "recall_at_k": "recall_at_k_avg",
    "reciprocal_rank": "mrr",  # mean of per-case reciprocal ranks
}


def aggregate_metrics(per_case_results: list[dict]) -> dict:
    """Average each metric over the cases where it applies.

    Unanswerable cases carry None metrics and are excluded per metric, so they
    neither lower the averages nor count in the divisor. A metric with no
    applicable cases is None, not 0.
    """
    summary = {}
    for case_key, summary_key in _AGGREGATE_KEYS.items():
        values = [case[case_key] for case in per_case_results if case[case_key] is not None]
        summary[summary_key] = sum(values) / len(values) if values else None
    return summary
