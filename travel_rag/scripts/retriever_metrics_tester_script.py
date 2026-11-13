import asyncio
from pathlib import Path
import httpx2
from app.config import get_settings
from app.embeddings.client import OllamaEmbeddingClient
from app.ingestion.doc_reader import load_cases
from app.retrieval.retriever import find_most_similar_chunks
from app.retrieval.retrieval_metrics import retrieval_metrics,aggregate_metrics


DATASET_PATH = (
    Path(__file__).resolve().parent.parent
    / "eval"
    / "datasets"
    / "rag_v1.jsonl"
)

async def retriever_metrics_testing() -> None:
    """Evaluate retriever metrics for the configured dataset."""
    settings = get_settings()
    async with httpx2.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout_seconds,
        ) as http_client:
        embedding_client = OllamaEmbeddingClient(
            http_client,
            settings.ollama_embedding_model,
        )
        metrics_result_avg=[]
        for cases in load_cases(DATASET_PATH):
            case_question,case_expected_chunk_ids = cases["question"],cases["expected_chunk_ids"]
            question_embedding = await embedding_client.embed(case_question)
            retrieved_chunks = find_most_similar_chunks(question_embedding, top_k=3)
            metrics_result = retrieval_metrics(expected_chunks_ids=case_expected_chunk_ids,retrieved_chunks_ids=retrieved_chunks["ids"][0],k=3)
            metrics_result_avg.append(metrics_result)
            print(f"\nmetric result --> {metrics_result}")
        final_metrics=aggregate_metrics(per_case_results=metrics_result_avg)
        print(f"aggregate metrics results :\n{final_metrics}")


if __name__ == "__main__":
    asyncio.run(retriever_metrics_testing())
