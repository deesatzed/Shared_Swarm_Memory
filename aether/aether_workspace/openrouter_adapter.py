#!/usr/bin/env python3
"""OpenRouter text, typed-decision, and embedding clients for Aether."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from model_config import (
    API_ROOT, DECISION_MODELS, EMBEDDING_MODELS, TEXT_MODELS, resolve_openrouter_key,
    selected_models,
)

from aether_core import (
    ConnectomeScaffoldGraph,
    FrozenLLMClient,
    HarnessConfig,
    HarnessDiff,
    MockFrozenLLM,
    ProposeProbeComposeEngine,
    ToolRegistry,
    TraceAnomalyReport,
)

logger = logging.getLogger("aether.openrouter")


class OpenRouterConfig(BaseModel):
    api_key: str = Field(default_factory=resolve_openrouter_key, repr=False, exclude=True)
    base_url: str = f"{API_ROOT}/chat/completions"
    decision_url: str = f"{API_ROOT}/systemone"
    embedding_url: str = f"{API_ROOT}/embeddings"
    default_model: str = Field(default_factory=lambda: selected_models("MODEL1", TEXT_MODELS)[0])
    fallback_models: list[str] = Field(default_factory=lambda: selected_models("MODEL1", TEXT_MODELS)[1:])
    decision_models: list[str] = Field(default_factory=lambda: selected_models("DECISION_MODEL", DECISION_MODELS), min_length=1)
    embedding_models: list[str] = Field(default_factory=lambda: selected_models("EMBED_MODEL", EMBEDDING_MODELS), min_length=1)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=64, le=8192)
    timeout_seconds: float = 30.0
    max_retries: int = Field(default=3, ge=1)
    app_url: str = "https://github.com/deesatzed/Shared_Swarm_Memory"
    app_title: str = "Aether-Decision-Swarm-Harness"


class OpenRouterRequestError(RuntimeError):
    """Safe error metadata; response bodies and authorization are never echoed."""

    def __init__(self, status_code: int | None) -> None:
        self.status_code = status_code
        super().__init__(f"OpenRouter request failed (HTTP {status_code or 'unavailable'})")


class OpenRouterFrozenLLM(FrozenLLMClient):
    def __init__(self, config: OpenRouterConfig | None = None) -> None:
        self.config = config or OpenRouterConfig()
        if not self.config.api_key:
            raise ValueError("OPENROUTER_API_KEY is missing.")
        self._client = httpx.Client(
            timeout=httpx.Timeout(self.config.timeout_seconds),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "HTTP-Referer": self.config.app_url,
                "X-Title": self.config.app_title,
                "Content-Type": "application/json",
            },
        )
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_calls = 0
        self.last_model: str | None = None
        self.last_usage: dict[str, Any] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OpenRouterFrozenLLM:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.config.default_model,
            "models": list(dict.fromkeys([self.config.default_model, *self.config.fallback_models])),
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        data = self._post_json(self.config.base_url, payload)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("OpenRouter returned no text completion") from None
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenRouter returned an empty text completion")
        return content.strip()

    def decide(
        self, state: Any, questions: dict[str, Any], *, model: str | None = None,
    ) -> dict[str, Any]:
        """Return typed System One answers, including their probabilities."""
        models = [model] if model is not None else self.config.decision_models
        for index, selected in enumerate(models):
            try:
                data = self._post_json(self.config.decision_url, {
                    "model": selected, "state": state, "questions": questions,
                })
            except OpenRouterRequestError as exc:
                if exc.status_code in {401, 402, 403} or index == len(models) - 1:
                    raise
                continue
            answers = data.get("answers")
            if not isinstance(answers, dict) or not questions.keys() <= answers.keys():
                raise RuntimeError("OpenRouter returned incomplete typed decisions")
            return data
        raise RuntimeError("No decision model configured")

    def embed(self, inputs: list[str], *, model: str | None = None) -> dict[str, Any]:
        """Embed with one explicit model. Alternatives use different vector spaces."""
        selected = model or self.config.embedding_models[0]
        data = self._post_json(self.config.embedding_url, {
            "model": selected, "input": inputs, "encoding_format": "float",
        })
        if not isinstance(data.get("data"), list) or len(data["data"]) != len(inputs):
            raise RuntimeError("OpenRouter returned incomplete embeddings")
        return data

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        status_code = None
        for attempt in range(self.config.max_retries):
            try:
                response = self._client.post(url, json=payload)
                status_code = response.status_code
                if response.is_success:
                    data = response.json()
                    if not isinstance(data, dict):
                        raise ValueError("Expected an object")
                    usage = data.get("usage") or {}
                    self.last_usage = usage
                    self.last_model = data.get("model")
                    self.total_prompt_tokens += usage.get("prompt_tokens", usage.get("input_tokens", 0))
                    self.total_completion_tokens += usage.get("completion_tokens", usage.get("output_tokens", 0))
                    self.total_calls += 1
                    return data
                if status_code in {400, 401, 402, 403, 404}:
                    break
            except (httpx.RequestError, ValueError):
                status_code = None
            if attempt + 1 < self.config.max_retries:
                time.sleep(0.75 * (2 ** attempt))
        raise OpenRouterRequestError(status_code)


class LiveProposeProbeComposeEngine(ProposeProbeComposeEngine):
    pass


def build_llm_client(
    model: str | None = None, *, credentials_file: str | Path | None = None,
) -> FrozenLLMClient:
    api_key = resolve_openrouter_key(credentials_file)
    if api_key:
        config = OpenRouterConfig(api_key=api_key)
        if model is not None:
            config.default_model = model
        return OpenRouterFrozenLLM(config)
    return MockFrozenLLM()
