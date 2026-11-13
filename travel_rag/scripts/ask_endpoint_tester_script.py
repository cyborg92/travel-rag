"""Run every eval case through the running POST /ask endpoint and save the results.

Start the API first (`uvicorn app.main:app`), then run from travel_rag/:
    ./.venv/bin/python -m scripts.ask_endpoint_tester_script

Each case is written to a JSONL results file as soon as it finishes, so a slow
or crashed run keeps what it has. The model name is read from settings, so run
this with the same TRAVEL_RAG_* environment as the server.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

import httpx2

from app.config import get_settings
from app.ingestion.doc_reader import load_cases

API_BASE_URL = "http://127.0.0.1:8000"
# Local reasoning models can take minutes per question, so this is much larger
# than the server's own Ollama timeout.
REQUEST_TIMEOUT_SECONDS = 300

EVAL_DIR = Path(__file__).resolve().parent.parent / "eval"
DATASET_PATH = EVAL_DIR / "datasets" / "rag_v1.jsonl"
RESULTS_DIR = EVAL_DIR / "results"


def score_case(case: dict, response: dict) -> dict:
    """Compute the checks that separate retrieval failures from generation failures."""
    retrieved_ids = [chunk["id"] for chunk in response["retrieved"]]
    cited_ids = [citation["id"] for citation in response["citations"]]
    expected_ids = case["expected_chunk_ids"]

    return {
        # None when the case has no expected chunks (unanswerable questions).
        "expected_in_retrieved": (
            all(chunk_id in retrieved_ids for chunk_id in expected_ids)
            if expected_ids
            else None
        ),
        "cited_expected_chunk": (
            any(chunk_id in expected_ids for chunk_id in cited_ids)
            if expected_ids
            else None
        ),
        "refusal_correct": response["refused"] == (not case["answerable"]),
    }


async def ask_one(http_client: httpx2.AsyncClient, case: dict) -> dict:
    record = {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "answerable": case["answerable"],
        "expected_chunk_ids": case["expected_chunk_ids"],
    }
    try:
        response = await http_client.post("/ask", json={"question": case["question"]})
    except httpx2.HTTPError as error:
        return {**record, "status": "error", "error": f"{type(error).__name__}: {error}"}

    if response.status_code != 200:
        return {**record, "status": response.status_code, "error": response.text[:500]}

    body = response.json()
    return {
        **record,
        "status": 200,
        "error": None,
        "answer": body["answer"],
        "refused": body["refused"],
        "cited_ids": [citation["id"] for citation in body["citations"]],
        "retrieved_ids": [chunk["id"] for chunk in body["retrieved"]],
        "latency_ms": body["latency_ms"],
        "prompt_tokens": body["token_usage"]["prompt_tokens"],
        "completion_tokens": body["token_usage"]["completion_tokens"],
        **score_case(case, body),
    }


def print_summary(records: list[dict]) -> None:
    succeeded = [r for r in records if r["status"] == 200]
    print(f"\nrequests succeeded: {len(succeeded)}/{len(records)}")
    for record in records:
        if record["status"] != 200:
            print(f"  {record['id']} FAILED status={record['status']} {record['error']}")
    answerable = [r for r in succeeded if r["expected_in_retrieved"] is not None]
    print(
        "expected chunks all in retrieved: "
        f"{sum(r['expected_in_retrieved'] for r in answerable)}/{len(answerable)}"
    )
    print(
        "refusal correct: "
        f"{sum(r['refusal_correct'] for r in succeeded)}/{len(succeeded)}"
    )


async def ask_endpoint_testing() -> None:
    model = get_settings().ollama_model
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    results_path = RESULTS_DIR / f"ask_{model.replace(':', '-')}_{stamp}.jsonl"
    print(f"model={model} results={results_path}")

    records = []
    async with httpx2.AsyncClient(
        base_url=API_BASE_URL, timeout=REQUEST_TIMEOUT_SECONDS
    ) as http_client:
        with results_path.open("w", encoding="utf-8") as results_file:
            for case in load_cases(DATASET_PATH):
                record = await ask_one(http_client, case)
                record["model"] = model
                records.append(record)
                results_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                results_file.flush()
                print(
                    f"{record['id']} status={record['status']} "
                    f"refused={record.get('refused')} "
                    f"in_retrieved={record.get('expected_in_retrieved')} "
                    f"latency_ms={record.get('latency_ms')}"
                )
    print_summary(records)


if __name__ == "__main__":
    asyncio.run(ask_endpoint_testing())
