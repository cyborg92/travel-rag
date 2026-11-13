from app.ingestion.chunker import chunk_section
from app.ingestion.doc_reader import load_documents
from app.retrieval.bm25 import BM25, PATTERN_1, PATTERN_2, PATTERN_3


def bm25_test() -> None:
    """bm25 policy testing"""
    chunks = [
        chunk
        for filename, text in load_documents()
        for chunk in chunk_section(text, filename)
    ]
    bm25 = BM25(chunks, pattern=PATTERN_2)  # swap the pattern here
    print(f"N={bm25.N}, avg_len={bm25.avg_len:.1f}, "
          f"unique terms={len(bm25.doc_freq)}")
    print(f"top terms: {bm25.doc_freq.most_common(5)}")

if __name__ == "__main__":
    bm25_test()