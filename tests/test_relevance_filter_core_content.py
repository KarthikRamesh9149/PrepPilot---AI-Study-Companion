from langchain_core.documents import Document

from exam_helper.services.relevance_filter import classify_chunks


def test_relevance_filter_core_content():
    chunks = [
        Document(
            page_content="Uniform Cost Search expands the node with lowest path cost g(n).",
            metadata={"chunk_id": "c2"},
        )
    ]
    labels = classify_chunks(chunks, topics=["Uniform Cost Search"])
    assert labels["c2"]["label"] in {"core_exam_content", "uncertain"}
    assert labels["c2"]["score"] > 0.2
