from pathlib import Path

def load_documents() -> list[tuple[str, str]]:
    DOCUMENT_DIR = Path(__file__).parent.parent.parent / "data" / "policies"
    documents = []
    for path in sorted(DOCUMENT_DIR.glob("*.md")):
        documents.append((path.name, path.read_text(encoding="utf-8")))
    return documents
