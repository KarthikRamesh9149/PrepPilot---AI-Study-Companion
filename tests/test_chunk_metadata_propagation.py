from langchain_core.documents import Document

from exam_helper.ingestion.chunking import chunk_documents


def test_chunk_metadata_propagation():
    docs = [
        Document(
            page_content="Topic A. " * 200,
            metadata={"source_file": "mod.pdf", "source_type": "pdf", "page_or_slide_number": 3},
        )
    ]

    chunks = chunk_documents(docs)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert "chunk_id" in chunk.metadata
        assert "snippet_reference" in chunk.metadata
        assert chunk.metadata["source_file"] == "mod.pdf"
        assert chunk.metadata["source_type"] == "pdf"
        assert chunk.metadata["page_or_slide_number"] == 3
