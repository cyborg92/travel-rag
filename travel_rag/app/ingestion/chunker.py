import re


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
    filename: str = "unknown",
) -> list[dict]:
    """
    Split text into character-sized chunks with the requested overlap.

    Args:
        text: The text to split.
        chunk_size: Maximum number of characters per chunk.
        overlap: Number of shared characters between adjacent chunks.
        filename: The name of the file containing the text.

    Returns:
        The resulting text chunks.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    if overlap < 0:
        raise ValueError("overlap must be a non-negative integer.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size.")
    chunks: list[dict] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(
            {
                "source": filename,
                "chunk_index": len(chunks),
                "chunk": chunk,
            }
        )
        if end >= text_length:
            break
        start += chunk_size - overlap
    return chunks


def chunk_section(text: str, filename: str = "unknown") -> list[dict]:
    """
    Split a document into sections based on a heading pattern.

    Args:
        text: The text to split.
        filename: The name of the file containing the text.

    Returns:
        The resulting text sections.
    """
    sections = re.split(r"(?m)(?=^## )", text)

    results = []
    for section in sections:
        if section.strip():
            heading = re.match(r"(?m)^##\s+(.+)$", section)
            heading_text = heading.group(1).strip() if heading else "Introduction"
            results.append(
                {
                    "source": filename,
                    "section": heading_text,
                    "chunk_index": len(results),
                    "chunk": section.strip(),
                }
            )
    return results
