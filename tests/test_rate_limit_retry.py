from exam_helper.services.groq_client import GroqClient


class _Resp:
    def __init__(self, headers):
        self.headers = headers


class _RateLimitError(Exception):
    def __init__(self, headers):
        super().__init__("rate limited")
        self.status_code = 429
        self.response = _Resp(headers)


def test_rate_limit_retry(monkeypatch):
    client = GroqClient(api_key="test-key")
    calls = {"count": 0}
    sleeps = []

    def fake_chat_once(messages_payload, model, temperature, max_tokens):
        calls["count"] += 1
        if calls["count"] == 1:
            raise _RateLimitError({"Retry-After": "0.1"})
        return '{"ok": true}'

    monkeypatch.setattr(client, "_chat_once", fake_chat_once)
    monkeypatch.setattr("exam_helper.services.groq_client.time.sleep", lambda sec: sleeps.append(sec))

    result, used_model = client.chat_json_with_fallback(system_prompt="s", user_prompt="u", model_chain=["m1"])
    assert result["ok"] is True
    assert used_model == "m1"
    assert len(sleeps) == 1
