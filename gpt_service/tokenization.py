"""Simple token counting helpers used to keep prompts within limits."""

from __future__ import annotations

import re
from dataclasses import dataclass

_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")


def simple_token_count(text: str) -> int:
    """Return a deterministic approximation of token usage.

    The helper intentionally avoids heavyweight dependencies such as ``tiktoken``
    so that it works in lightweight environments.  The implementation is
    obviously not model-accurate, but it is more than sufficient to prevent most
    accidental token explosions before the request is sent to the model.
    """

    if not text:
        return 0
    return len(_TOKEN_PATTERN.findall(text))


@dataclass(slots=True)
class TokenBudget:
    """Utility class for enforcing prompt and completion limits."""

    max_input_tokens: int
    max_output_tokens: int

    def validate_prompt(self, prompt: str) -> None:
        tokens = simple_token_count(prompt)
        if tokens > self.max_input_tokens:
            raise TokenLimitError(
                "Prompt exceeds the maximum number of tokens.",
                tokens=tokens,
                limit=self.max_input_tokens,
            )

    def clamp_output(self, text: str) -> str:
        tokens = simple_token_count(text)
        if tokens <= self.max_output_tokens:
            return text
        # Crude truncation strategy that still honours multi-byte characters.
        running = 0
        result: list[str] = []
        for match in _TOKEN_PATTERN.finditer(text):
            running += 1
            result.append(match.group(0))
            if running >= self.max_output_tokens:
                break
        return "".join(result)


from .exceptions import TokenLimitError

__all__ = ["TokenBudget", "simple_token_count"]
