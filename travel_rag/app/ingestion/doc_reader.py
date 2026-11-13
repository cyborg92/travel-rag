from pathlib import Path
import json


def load_documents() -> list[tuple[str, str]]:
    """Load all markdown policy documents from the data directory."""
    document_dir = Path(__file__).parent.parent.parent / "data" / "policies"
    documents = []
    for path in sorted(document_dir.glob("*.md")):
        documents.append((path.name, path.read_text(encoding="utf-8")))
    return documents


def load_cases(path):
    """Load JSONL cases from a file path."""
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases
