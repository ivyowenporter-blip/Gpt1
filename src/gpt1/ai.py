"""AI helper utilities with lightweight security features."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict


SENSITIVE_PATTERNS = (
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
)


def scrub_sensitive_data(payload: str) -> str:
    """Mask obvious secrets to avoid leaking through prompts/logs."""

    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        return word[0] + "*" * max(len(word) - 2, 0) + word[-1]

    result = payload
    for pattern in SENSITIVE_PATTERNS:
        result = pattern.sub(replace, result)
    return result


@dataclass
class PromptTemplateAIAgent:
    """Generates deterministic responses based on a template."""

    model_name: str = "mock-gpt"
    llm_client: Callable[[str], str] | None = None

    def __post_init__(self) -> None:
        if self.llm_client is None:
            self.llm_client = lambda prompt: f"[mock-response:{self.model_name}] {prompt[::-1]}"

    def build_prompt(self, context: str, question: str) -> str:
        safe_context = scrub_sensitive_data(context)
        safe_question = scrub_sensitive_data(question)
        return f"Model={self.model_name}\nContext:\n{safe_context}\nQuestion:\n{safe_question}\n"

    def generate(self, context: str, question: str) -> Dict[str, str]:
        prompt = self.build_prompt(context, question)
        response = self.llm_client(prompt)
        return {"prompt": prompt, "response": response}
