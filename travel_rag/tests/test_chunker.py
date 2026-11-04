import pytest

from app.utils.chunker import chunk_section, chunk_text


def test_chunk_text_splits_with_character_overlap() -> None:
    chunks = chunk_text(
        "ABCDEFGHIJ",
        chunk_size=4,
        overlap=1,
        filename="policy.md",
    )

    assert chunks == [
        {"source": "policy.md", "chunk_index": 0, "chunk": "ABCD"},
        {"source": "policy.md", "chunk_index": 1, "chunk": "DEFG"},
        {"source": "policy.md", "chunk_index": 2, "chunk": "GHIJ"},
    ]


def test_chunk_text_returns_empty_list_for_empty_text() -> None:
    assert chunk_text("", chunk_size=4, overlap=1) == []


def test_chunk_text_keeps_text_shorter_than_chunk_size_in_one_chunk() -> None:
    assert chunk_text(
        "ABC",
        chunk_size=4,
        overlap=1,
        filename="policy.md",
    ) == [{"source": "policy.md", "chunk_index": 0, "chunk": "ABC"}]


def test_chunk_text_returns_short_final_chunk_without_extra_chunk() -> None:
    chunks = chunk_text(
        "ABCDEFGH",
        chunk_size=3,
        overlap=1,
        filename="policy.md",
    )

    assert chunks == [
        {"source": "policy.md", "chunk_index": 0, "chunk": "ABC"},
        {"source": "policy.md", "chunk_index": 1, "chunk": "CDE"},
        {"source": "policy.md", "chunk_index": 2, "chunk": "EFG"},
        {"source": "policy.md", "chunk_index": 3, "chunk": "GH"},
    ]


def test_chunk_section_keeps_source_and_section_heading() -> None:
    chunks = chunk_section(
        "# Travel policy\n\n## Scope\nApplies to all tickets.\n\n"
        "## Exceptions\nInfant rules differ.",
        filename="policy.md",
    )

    assert chunks == [
        {
            "source": "policy.md",
            "section": "Introduction",
            "chunk_index": 0,
            "chunk": "# Travel policy",
        },
        {
            "source": "policy.md",
            "section": "Scope",
            "chunk_index": 1,
            "chunk": "## Scope\nApplies to all tickets.",
        },
        {
            "source": "policy.md",
            "section": "Exceptions",
            "chunk_index": 2,
            "chunk": "## Exceptions\nInfant rules differ.",
        },
    ]


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
