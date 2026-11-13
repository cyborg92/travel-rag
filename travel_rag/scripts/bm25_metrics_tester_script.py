from pathlib import Path
from app.ingestion.doc_reader import load_cases, load_documents
from app.ingestion.chunker import chunk_section
from app.retrieval.retrieval_metrics import retrieval_metrics,aggregate_metrics
from app.retrieval.bm25 import BM25, PATTERN_2


DATASET_PATH = (
    Path(__file__).resolve().parent.parent
    / "eval"
    / "datasets"
    / "rag_v1.jsonl"
)

def bm25_metrics_testing() -> None:
    """Evaluate bm25  metrics for the configured dataset."""
    metrics_result_avg=[]
    chunks = [
            chunk
            for filename, text in load_documents()
            for chunk in chunk_section(text, filename)
        ]
    bm25 = BM25(chunks, pattern=PATTERN_2)  # swap the pattern here
    for cases in load_cases(DATASET_PATH):
        case_question,case_expected_chunk_ids = cases["question"],cases["expected_chunk_ids"]
        results = bm25.search(case_question, top_k=3)
        retrieved_ids = [chunk_id for chunk_id, _ in results]
        print (f"retrieved ids bm25{retrieved_ids}")

        metrics_result = retrieval_metrics(expected_chunks_ids=case_expected_chunk_ids,retrieved_chunks_ids=retrieved_ids,k=3)
        metrics_result_avg.append(metrics_result)
        print(f"\nmetric result --> {metrics_result}")
    final_metrics=aggregate_metrics(per_case_results=metrics_result_avg)
    print(f"aggregate metrics results :\n{final_metrics}")

if __name__ == "__main__":
    bm25_metrics_testing()
