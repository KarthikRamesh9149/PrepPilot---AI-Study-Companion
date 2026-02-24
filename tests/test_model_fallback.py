from exam_helper.services.groq_client import GroqClient


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
