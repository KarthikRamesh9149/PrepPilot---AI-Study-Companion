from langchain_core.documents import Document

from exam_helper.services.relevance_filter import allowed_chunk_ids


def test_retrieval_excludes_admin_by_default():
    chunks = [
        Document(page_content="x", metadata={"chunk_id": "a", "relevance_label": "admin_meta", "is_restored": False}),
        Document(page_content="y", metadata={"chunk_id": "b", "relevance_label": "core_exam_content", "is_restored": False}),
    ]
    allowed = allowed_chunk_ids(chunks)
    assert "a" not in allowed
    assert "b" in allowed
