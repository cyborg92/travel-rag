import pytest

from app.utils.chunker import chunk_text


def test_chunk_text_splits_with_character_overlap() -> None:
    chunks = chunk_text("ABCDEFGHIJ", chunk_size=4, overlap=1)

    assert chunks == ["ABCD", "DEFG", "GHIJ"]


def test_chunk_text_returns_empty_list_for_empty_text() -> None:
    assert chunk_text("", chunk_size=4, overlap=1) == []


def test_chunk_text_keeps_text_shorter_than_chunk_size_in_one_chunk() -> None:
    assert chunk_text("ABC", chunk_size=4, overlap=1) == ["ABC"]


def test_chunk_text_returns_short_final_chunk_without_extra_chunk() -> None:
    chunks = chunk_text("ABCDEFGH", chunk_size=3, overlap=1)

    assert chunks == ["ABC", "CDE", "EFG", "GH"]


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [
        (0, 0),
        (-1, 0),
        (4, -1),
        (4, 4),
        (4, 5),
    ],
)
def test_chunk_text_rejects_invalid_size_or_overlap(
    chunk_size: int,
    overlap: int,
) -> None:
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=chunk_size, overlap=overlap)
