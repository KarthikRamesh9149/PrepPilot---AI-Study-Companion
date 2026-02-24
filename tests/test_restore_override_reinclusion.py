from langchain_core.documents import Document

from exam_helper.services.relevance_filter import allowed_chunk_ids, apply_relevance_labels


def test_restore_override_reinclusion():
    chunks = [Document(page_content="x", metadata={"chunk_id": "a"})]
    labels = {"a": {"label": "admin_meta", "score": 0.2, "reason_codes": ["policy_language"]}}
    enriched = apply_relevance_labels(chunks, labels, overrides={"a": True})
    allowed = allowed_chunk_ids(enriched)
    assert "a" in allowed
