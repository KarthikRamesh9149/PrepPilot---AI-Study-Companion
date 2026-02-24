from pathlib import Path


def test_ui_copy_no_jargon():
    text = Path("app.py").read_text(encoding="utf-8").lower()
    banned = ["ingestion status", "no context retrieved from vector database", "not found in your module p/s 1"]
    for token in banned:
        assert token not in text
