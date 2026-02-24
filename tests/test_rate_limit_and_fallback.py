from exam_helper.services.groq_client import GroqClient


class _Resp:
    def __init__(self, headers):
        self.headers = headers


class _RateLimitError(Exception):
    def __init__(self, headers):
        super().__init__("rate limited")
        self.status_code = 429
        self.response = _Resp(headers)


def test_rate_limit_retry_with_retry_after(monkeypatch):
    client = GroqClient(api_key="test-key")
    calls = {"count": 0}
    sleeps = []
    messages = []

    def fake_chat_once(messages_payload, model, temperature, max_tokens):
        calls["count"] += 1
        if calls["count"] == 1:
            raise _RateLimitError({"Retry-After": "0.2"})
        return '{"ok": true}'

    monkeypatch.setattr(client, "_chat_once", fake_chat_once)
    monkeypatch.setattr("exam_helper.services.groq_client.time.sleep", lambda sec: sleeps.append(sec))

    result, used_model = client.chat_json_with_fallback(
        system_prompt="s",
        user_prompt="u",
        model_chain=["model-a"],
        status_callback=lambda msg: messages.append(msg),
    )

    assert result["ok"] is True
    assert used_model == "model-a"
    assert len(sleeps) == 1
    assert any("Rate limited by Groq" in msg for msg in messages)


def test_model_fallback(monkeypatch):
    client = GroqClient(api_key="test-key")
    attempted = []

    def fake_chat_once(messages_payload, model, temperature, max_tokens):
        attempted.append(model)
        if model == "first-model":
            raise Exception("model failure")
        return '{"value": 1}'

    monkeypatch.setattr(client, "_chat_once", fake_chat_once)

    result, used_model = client.chat_json_with_fallback(
        system_prompt="s",
        user_prompt="u",
        model_chain=["first-model", "second-model"],
    )

    assert result["value"] == 1
    assert used_model == "second-model"
    assert attempted == ["first-model", "second-model"]
