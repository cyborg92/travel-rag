from pathlib import Path

from app.ingestion.chunker import chunk_section
from app.ingestion.doc_reader import load_cases, load_documents

DATASET_PATH = Path(__file__).resolve().parent.parent / "eval" / "datasets" / "rag_v1.jsonl"
REQUIRED_FIELDS = {"id", "category", "question", "answerable", "expected_chunk_ids", "reference_answer", "rubric"}


def corpus_chunk_ids() -> set[str]:
    """ for corpus chunks ids process"""
    return {
        f"{chunk['source']}:{chunk['chunk_index']}"
        for filename, text in load_documents()
        for chunk in chunk_section(text, filename)
    }


def test_cases_have_required_fields_and_unique_ids() -> None:
    """ for  unique id test cases"""
    cases = load_cases(DATASET_PATH)

    assert all(REQUIRED_FIELDS <= case.keys() for case in cases)
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))


def test_expected_chunk_ids_exist_in_the_current_corpus() -> None:
    known_ids = corpus_chunk_ids()

    for case in load_cases(DATASET_PATH):
        missing = [i for i in case["expected_chunk_ids"] if i not in known_ids]
        assert not missing, f"{case['id']} expects unknown chunks {missing}"


def test_unanswerable_cases_have_no_expected_chunks() -> None:
    for case in load_cases(DATASET_PATH):
        if not case["answerable"]:
            assert case["expected_chunk_ids"] == [], case["id"]
