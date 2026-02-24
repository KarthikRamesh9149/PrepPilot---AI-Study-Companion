from langchain_core.documents import Document

from exam_helper.services.relevance_filter import classify_chunks


def test_relevance_filter_admin_chunks():
    chunks = [
        Document(
            page_content="Academic integrity and plagiarism policy on Canvas discussion board.",
            metadata={"chunk_id": "c1"},
        )
    ]
    labels = classify_chunks(chunks, topics=["Search Algorithms"])
    assert labels["c1"]["label"] == "admin_meta"
