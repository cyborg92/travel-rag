from typing import Any

def builder_context(results: dict[str, Any]) -> str:
    context_parts: list[str] = []
    for rank, (chunk_id, document, metadata) in enumerate(
        zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
        ),
        start=1,
    ):
        context_parts.append(
            f"[Source {rank} | ID: {chunk_id} | File: {metadata['source']} | "
            f"Section: {metadata['section']}]\n{document}"
        )

    return "\n\n".join(context_parts)