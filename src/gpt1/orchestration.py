"""Task orchestration loop for browser + AI automation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .ai import PromptTemplateAIAgent
from .browser import BrowserSession, BrowserAction


@dataclass
class OrchestrationStep:
    """Declarative instruction for the orchestrator."""

    description: str
    url: str
    question: str


@dataclass
class OrchestrationResult:
    steps_executed: List[OrchestrationStep]
    browser_actions: List[BrowserAction]
    ai_transcripts: List[str]


class TaskOrchestrator:
    """Runs a deterministic loop that alternates browser + AI work."""

    def __init__(self, browser: BrowserSession, agent: PromptTemplateAIAgent, max_steps: int = 10):
        self.browser = browser
        self.agent = agent
        self.max_steps = max_steps

    def run(self, plan: Sequence[OrchestrationStep]) -> OrchestrationResult:
        executed: List[OrchestrationStep] = []
        transcripts: List[str] = []

        for idx, step in enumerate(plan):
            if idx >= self.max_steps:
                break
            page = self.browser.open_page(step.url)
            transcripts.append(self.agent.generate(page, step.question)["response"])
            executed.append(step)

        return OrchestrationResult(
            steps_executed=executed,
            browser_actions=self.browser.snapshot(),
            ai_transcripts=transcripts,
        )
