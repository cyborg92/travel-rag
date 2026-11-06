from app.rag.response_formatter import (
    build_citation_response_obj,
    build_retrieved_response_obj,
    chat_refused_response_flag,
)


def test_build_citations_maps_short_and_full_labels_to_chroma_results() -> None:
    retrieved_chunks = {
        "ids": [["baggage.md:2", "baggage.md:3"]],
        "documents": [["Cabin baggage.", "Checked baggage."]],
        "metadatas": [[
            {
                "source": "baggage.md",
                "section": "Cabin baggage",
                "chunk_index": 2,
            },
            {
                "source": "baggage.md",
                "section": "Checked baggage",
                "chunk_index": 3,
            },
        ]],
        "distances": [[0.4, 0.6]],
    }
    answer = (
        "Cabin bags are allowed [Source 1]. "
        "The checked allowance is listed here "
        "[Source 2 | ID: untrusted.md:99 | File: wrong.md | Section: Wrong]. "
        "Again, [source 1]."
    )

    citations = build_citation_response_obj(answer, retrieved_chunks)

    assert citations == [
        {
            "label": "Source 1",
            "id": "baggage.md:2",
            "source": "baggage.md",
            "section": "Cabin baggage",
            "chunk_index": 2,
        },
        {
            "label": "Source 2",
            "id": "baggage.md:3",
            "source": "baggage.md",
            "section": "Checked baggage",
            "chunk_index": 3,
        },
    ]


def test_build_citations_ignores_labels_without_a_matching_retrieved_result() -> None:
    retrieved_chunks = {
        "ids": [["baggage.md:2"]],
        "documents": [["Cabin baggage."]],
        "metadatas": [[{"source": "baggage.md", "section": "Cabin baggage"}]],
        "distances": [[0.4]],
    }

    citations = build_citation_response_obj(
        "Unknown [Source 0] and [Source 2] labels.",
        retrieved_chunks,
    )

    assert citations == []


def test_build_retrieved_response_obj_returns_every_match_with_distance() -> None:
    retrieved_chunks = {
        "ids": [["baggage.md:2", "baggage.md:3"]],
        "documents": [["Cabin baggage.", "Checked baggage."]],
        "metadatas": [[{}, {}]],
        "distances": [[0.4, 0.6]],
    }

    assert build_retrieved_response_obj(retrieved_chunks) == [
        {"id": "baggage.md:2", "distance": 0.4},
        {"id": "baggage.md:3", "distance": 0.6},
    ]


def test_chat_refused_response_flag_detects_insufficient_context_phrase() -> None:
    assert chat_refused_response_flag(
        "I cannot answer due to insufficient context."
    )
    assert not chat_refused_response_flag(
        "Business class allows two cabin bags [Source 1]."
    )
