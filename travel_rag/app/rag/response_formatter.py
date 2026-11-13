import re
from typing import Any


CITATION_RE = re.compile(
    r"\[\s*Source\s+(\d+)(?:\s*\|[^\]]*)?\s*\]",
    re.IGNORECASE,
)


def build_retrieved_response_obj(
    retrieved_chunks: dict[str, Any],
) -> list[dict[str, Any]]:
    formatted_chunks = []
    for i, chunk_id in enumerate(retrieved_chunks["ids"][0]):
        chunk_info = {
            "id": chunk_id,
            "distance": retrieved_chunks["distances"][0][i],
        }
        formatted_chunks.append(chunk_info)
    return formatted_chunks


def build_citation_response_obj(
    answer: str,
    retrieved_chunks: dict[str, Any],
) -> list[dict[str, Any]]:
    ids = retrieved_chunks["ids"][0]
    metadatas = retrieved_chunks["metadatas"][0]
    citations = []
    seen_sources: set[int] = set()

    for match in CITATION_RE.finditer(answer):
        source_number = int(match.group(1))
        result_index = source_number - 1
        if (
            source_number in seen_sources
            or result_index < 0
            or result_index >= len(ids)
            or result_index >= len(metadatas)
        ):
            continue

        metadata = metadatas[result_index] or {}
        citation = {
            "label": f"Source {source_number}",
            "id": ids[result_index],
        }
        for key in ("source", "section", "chunk_index"):
            if key in metadata:
                citation[key] = metadata[key]
        citations.append(citation)
        seen_sources.add(source_number)

    return citations
