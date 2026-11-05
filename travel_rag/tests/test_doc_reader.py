from app.ingestion.doc_reader import load_documents


def test_load_documents_returns_all_policy_markdown_files() -> None:
    documents = load_documents()

    expected_filenames = [
        "disruption-policy.md",
        "new-baggage-policy.md",
        "new-cancellation-policy.md",
        "new-ticket-change-policy.md",
    ]
    filenames = [filename for filename, _ in documents]

    assert filenames == expected_filenames
    assert all(text.strip() for _, text in documents)