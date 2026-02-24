from __future__ import annotations

import json
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable

from openai import OpenAI

from exam_helper.config import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT_SECONDS


class GroqClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.groq.com/openai/v1",
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)

    def list_models(self) -> list[str]:
        models = self.client.models.list()
        return sorted([model.id for model in models.data])

    @staticmethod
    def _parse_retry_after(headers: dict | None) -> float | None:
        if not headers:
            return None
        value = headers.get("Retry-After") or headers.get("retry-after")
        if not value:
            return None

        try:
            return float(value)
        except ValueError:
            try:
                when = parsedate_to_datetime(value)
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                delta = (when - datetime.now(timezone.utc)).total_seconds()
                return max(delta, 0.0)
            except Exception:
                return None

    @staticmethod
    def _extract_json(content: str) -> dict:
        text = content.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or start >= end:
                raise
            return json.loads(text[start : end + 1])

    @staticmethod
    def _is_rate_limited(exc: Exception) -> tuple[bool, dict | None]:
        status_code = getattr(exc, "status_code", None)
        response = getattr(exc, "response", None)
        headers = getattr(response, "headers", None)
        if status_code == 429:
            return True, headers
        return False, headers

    def _chat_once(self, messages: list[dict], model: str, temperature: float, max_tokens: int) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Model returned empty content")
        return content

    def chat_json_with_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        model_chain: list[str],
        temperature: float = 0.2,
        max_tokens: int = 4000,
        status_callback: Callable[[str], None] | None = None,
    ) -> tuple[dict, str]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_error: Exception | None = None

        for model in model_chain:
            attempt = 0
            while attempt <= self.max_retries:
                try:
                    raw = self._chat_once(messages, model, temperature, max_tokens)
                    return self._extract_json(raw), model
                except Exception as exc:
                    last_error = exc
                    rate_limited, headers = self._is_rate_limited(exc)
                    if rate_limited and attempt < self.max_retries:
                        retry_after = self._parse_retry_after(headers)
                        if retry_after is None:
                            retry_after = min(20.0, 2 ** attempt) + random.uniform(0.0, 0.5)
                        if status_callback:
                            status_callback(f"Rate limited by Groq. Retrying in {retry_after:.1f} seconds...")
                        time.sleep(retry_after)
                        attempt += 1
                        continue
                    break

            if status_callback:
                status_callback(f"Model {model} failed. Trying fallback model...")

        raise RuntimeError(f"All model attempts failed. Last error: {last_error}")
