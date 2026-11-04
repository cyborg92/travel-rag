def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    """
    Split text into character-sized chunks with the requested overlap.

    Args:
        text: The text to split.
        chunk_size: Maximum number of characters per chunk.
        overlap: Number of shared characters between adjacent chunks.

    Returns:
        The resulting text chunks.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    if overlap < 0:
        raise ValueError("overlap must be a non-negative integer.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size.")
    chunks: list[str] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= text_length:
            break
        start += chunk_size - overlap
    return chunks