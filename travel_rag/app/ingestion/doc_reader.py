from pathlib import Path


def load_documents() -> list[tuple[str, str]]:
    document_dir = Path(__file__).parent.parent.parent / "data" / "policies"
    documents = []
    for path in sorted(document_dir.glob("*.md")):
        documents.append((path.name, path.read_text(encoding="utf-8")))
    return documents
