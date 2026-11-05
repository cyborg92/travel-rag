from app.rag.context_builder import builder_context


def test_builder_context_preserves_retrieval_order_and_labels_sources() -> None:
    results = {
        "ids": [["policy.md:2", "policy.md:3"]],
        "documents": [["Cabin baggage rules.", "Checked baggage rules."]],
        "metadatas": [[
            {"source": "policy.md", "section": "Cabin baggage"},
            {"source": "policy.md", "section": "Checked baggage"},
        ]],
        "distances": [[0.4, 0.6]],
    }

    context = builder_context(results)

    assert context.index("[Source 1 | ID: policy.md:2") < context.index(
        "[Source 2 | ID: policy.md:3"
    )
    assert "File: policy.md | Section: Cabin baggage" in context
    assert "Cabin baggage rules." in context
    assert "File: policy.md | Section: Checked baggage" in context
    assert "Checked baggage rules." in context


def test_builder_context_returns_empty_string_when_there_are_no_matches() -> None:
    results = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }

    assert builder_context(results) == ""
