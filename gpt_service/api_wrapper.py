"""Wrapper around an external chat/completions API with retries and logging."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import requests

from .exceptions import TokenLimitError
from .tokenization import TokenBudget, simple_token_count

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class APIConfig:
    """Configuration for interacting with an external LLM provider."""

    base_url: str
    api_key: str
    model: str
    max_input_tokens: int = 4096
    max_output_tokens: int = 1024
    max_retries: int = 3
    timeout: float = 30.0
    backoff_factor: float = 2.0
    user_agent: str = "gpt-service/1.0"


@dataclass(slots=True)
class APIResponse:
    """Normalized response from the language model."""

    prompt: str
    completion: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    raw: Dict[str, Any]


class ExternalAPIClient:
    """Simple helper that adds robustness when calling external APIs."""

    def __init__(self, config: APIConfig, session: Optional[requests.Session] = None) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.budget = TokenBudget(config.max_input_tokens, config.max_output_tokens)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": self.config.user_agent,
        }

    def generate(self, prompt: str, *, temperature: float = 0.7, extra: Optional[Dict[str, Any]] = None) -> APIResponse:
        """Send a prompt to the provider, handling retries and token limits."""

        self.budget.validate_prompt(prompt)
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": self.config.max_output_tokens,
        }
        if extra:
            payload.update(extra)

        for attempt in range(1, self.config.max_retries + 1):
            try:
                LOGGER.debug("Sending request to %s (attempt %s)", self.config.base_url, attempt)
                response = self.session.post(
                    self.config.base_url,
                    json=payload,
                    timeout=self.config.timeout,
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
                completion_text = self._extract_text(data)
                trimmed_completion = self.budget.clamp_output(completion_text)
                prompt_tokens = simple_token_count(prompt)
                completion_tokens = simple_token_count(trimmed_completion)
                return APIResponse(
                    prompt=prompt,
                    completion=trimmed_completion,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    raw=data,
                )
            except requests.RequestException as exc:
                LOGGER.warning("External API request failed (attempt %s/%s): %s", attempt, self.config.max_retries, exc)
                if attempt >= self.config.max_retries:
                    raise
                sleep_for = self.config.backoff_factor ** (attempt - 1)
                LOGGER.debug("Sleeping for %.2fs before retrying", sleep_for)
                time.sleep(sleep_for)

        raise RuntimeError("Unreachable")

    def _extract_text(self, data: Dict[str, Any]) -> str:
        """Try to normalize the completion field from popular APIs."""

        if "choices" in data:
            choices = data["choices"]
            if isinstance(choices, Iterable):
                for choice in choices:
                    # OpenAI style responses
                    message = choice.get("message") if isinstance(choice, dict) else None
                    if message and "content" in message:
                        return str(message["content"]).strip()
                    if "text" in choice:
                        return str(choice["text"]).strip()
        if "completion" in data:
            return str(data["completion"])  # generic
        raise ValueError("Unable to extract completion text from response.")


__all__ = ["ExternalAPIClient", "APIConfig", "APIResponse"]
