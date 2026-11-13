"""Compare semantic, BM25, and hybrid (RRF) retrieval on the eval dataset.

Run from travel_rag/ with Ollama up:
    ./.venv/bin/python -m scripts.hybrid_metrics_tester_script
"""
import asyncio
from pathlib import Path

import httpx2

from app.config import get_settings
from app.embeddings.client import OllamaEmbeddingClient
from app.ingestion.chunker import chunk_section
from app.ingestion.doc_reader import load_cases, load_documents
from app.retrieval.bm25 import BM25, PATTERN_2
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.retrieval_metrics import aggregate_metrics, retrieval_metrics
from app.retrieval.retriever import find_most_similar_chunks

DATASET_PATH = Path(__file__).resolve().parent.parent / "eval" / "datasets" / "rag_v1.jsonl"
K = 3  # cutoff used for scoring
CANDIDATES = 10  # each retriever supplies this many IDs to the fusion


async def hybrid_metrics_testing() -> None:
    settings = get_settings()
    chunks = [c for name, text in load_documents() for c in chunk_section(text, name)]
    bm25 = BM25(chunks, pattern=PATTERN_2)
    per_strategy: dict[str, list[dict]] = {"semantic": [], "bm25": [], "hybrid": []}

    async with httpx2.AsyncClient(
        base_url=settings.ollama_base_url, timeout=settings.ollama_timeout_seconds
    ) as http_client:
        embedder = OllamaEmbeddingClient(http_client, settings.ollama_embedding_model)
        for case in load_cases(DATASET_PATH):
            question, expected = case["question"], case["expected_chunk_ids"]
            vector = await embedder.embed(question)
            semantic_ids = find_most_similar_chunks(vector, top_k=CANDIDATES)["ids"][0]
            bm25_ids = [cid for cid, _ in bm25.search(question, top_k=CANDIDATES)]
            ranked = {
                "semantic": semantic_ids,
                "bm25": bm25_ids,
                "hybrid": reciprocal_rank_fusion([semantic_ids, bm25_ids]),
            }
            line = []
            for name, ids in ranked.items():
                metrics = retrieval_metrics(expected, ids[:K], k=K)
                per_strategy[name].append(metrics)
                recall = metrics["recall_at_k"]
                line.append(f"{name}={'-' if recall is None else round(recall, 2)}")
            print(f"{case['id']} recall@{K}: " + "  ".join(line))

    print(f"\n{'strategy':<10}{'hit@3':>8}{'prec@3':>8}{'recall@3':>10}{'mrr':>8}")
    for name, results in per_strategy.items():
        summary = aggregate_metrics(results)
        print(
            f"{name:<10}{summary['hit_at_k_avg']:>8.3f}{summary['precision_at_k_avg']:>8.3f}"
            f"{summary['recall_at_k_avg']:>10.3f}{summary['mrr']:>8.3f}"
        )


if __name__ == "__main__":
    asyncio.run(hybrid_metrics_testing())
