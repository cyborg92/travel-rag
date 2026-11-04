from app.utils.chunker import chunk_section
from app.utils.doc_reader import load_documents

def embedding_test() -> str:
    docs = load_documents()
    chunk_details = []
    doc_select=docs[0]
    chunks = chunk_section(doc_select[1], doc_select[0])
    chunk_details.append(f"{doc_select[0]}: {len(chunks)} chunks")