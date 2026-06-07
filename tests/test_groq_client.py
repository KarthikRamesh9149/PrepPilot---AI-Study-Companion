from __future__ import annotations

import pytest

from exam_helper.services.groq_client import GroqClient


def test_extract_json_accepts_markdown_wrapped_object() -> None:
    payload = GroqClient._extract_json('```json\n{"ok": true, "count": 2}\n```')

    assert payload == {"ok": True, "count": 2}


def test_extract_json_raises_when_no_object_is_present() -> None:
    with pytest.raises(ValueError):
        GroqClient._extract_json("no structured payload")
