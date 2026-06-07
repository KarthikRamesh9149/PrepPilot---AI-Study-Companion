from __future__ import annotations

import importlib

import exam_helper.config as config


def test_invalid_numeric_env_vars_fall_back_to_defaults(monkeypatch) -> None:
    monkeypatch.setenv("MAX_RETRIES", "not-an-int")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "not-a-float")

    reloaded = importlib.reload(config)

    assert reloaded.DEFAULT_MAX_RETRIES == 1
    assert reloaded.DEFAULT_TIMEOUT_SECONDS == 30.0

    importlib.reload(config)
