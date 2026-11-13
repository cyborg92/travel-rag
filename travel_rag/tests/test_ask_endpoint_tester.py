import asyncio

import httpx2

from scripts.ask_endpoint_tester_script import ask_one, score_case

CASE = {
    "id": "q1",
    "category": "direct",
    "question": "Q?",
    "answerable": True,
    "expected_chunk_ids": ["a:1"],
}
UNANSWERABLE = {**CASE, "id": "q2", "answerable": False, "expected_chunk_ids": []}


def ask_response(retrieved, cited, refused):
    return {
        "answer": "x",
        "retrieved": [{"id": chunk_id, "distance": 0.5} for chunk_id in retrieved],
        "citations": [{"id": chunk_id} for chunk_id in cited],
        "refused": refused,
        "latency_ms": 12.0,
        "token_usage": {"prompt_tokens": 1, "completion_tokens": 2},
    }


def test_score_case_flags_retrieval_hit_and_citation() -> None:
    scores = score_case(CASE, ask_response(["b:1", "a:1"], ["a:1"], False))

    assert scores == {
        "expected_in_retrieved": True,
        "cited_expected_chunk": True,
        "refusal_correct": True,
    }


def test_score_case_distinguishes_retrieval_miss_from_ignored_chunk() -> None:
    miss = score_case(CASE, ask_response(["b:1"], [], False))
    ignored = score_case(CASE, ask_response(["a:1"], [], False))

    assert miss["expected_in_retrieved"] is False
    assert ignored["expected_in_retrieved"] is True
    assert ignored["cited_expected_chunk"] is False


def test_score_case_unanswerable_has_no_retrieval_checks() -> None:
    answered = score_case(UNANSWERABLE, ask_response(["a:1"], [], False))
    refused = score_case(UNANSWERABLE, ask_response(["a:1"], [], True))

    assert answered["expected_in_retrieved"] is None
    assert answered["refusal_correct"] is False
    assert refused["refusal_correct"] is True


def run_ask_one(handler) -> dict:
    async def run() -> dict:
        transport = httpx2.MockTransport(handler)
        async with httpx2.AsyncClient(transport=transport, base_url="http://test") as client:
            return await ask_one(client, CASE)

    return asyncio.run(run())


def test_ask_one_records_success() -> None:
    record = run_ask_one(
        lambda request: httpx2.Response(200, json=ask_response(["a:1"], ["a:1"], False))
    )

    assert record["status"] == 200
    assert record["retrieved_ids"] == ["a:1"]
    assert record["expected_in_retrieved"] is True


def test_ask_one_records_http_error_instead_of_raising() -> None:
    record = run_ask_one(lambda request: httpx2.Response(504, json={"detail": "timeout"}))

    assert record["status"] == 504
    assert "timeout" in record["error"]


def test_ask_one_records_connection_failure() -> None:
    def handler(request):
        raise httpx2.ConnectError("refused")

    record = run_ask_one(handler)

    assert record["status"] == "error"
    assert "ConnectError" in record["error"]
