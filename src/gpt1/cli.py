"""Command-line entry point for running the orchestration loop."""
from __future__ import annotations

import json
import os
from dataclasses import asdict

from .ai import PromptTemplateAIAgent
from .browser import BrowserSession
from .orchestration import OrchestrationStep, TaskOrchestrator


def run_from_env() -> None:
    base_url = os.environ.get("BROWSER_BASE_URL", "https://example.com")
    model_name = os.environ.get("AI_MODEL_NAME", "mock-gpt")
    max_steps = int(os.environ.get("ORCHESTRATOR_MAX_STEPS", "5"))

    browser = BrowserSession(base_url=base_url)
    agent = PromptTemplateAIAgent(model_name=model_name)
    orchestrator = TaskOrchestrator(browser=browser, agent=agent, max_steps=max_steps)

    default_plan = [
        OrchestrationStep(description="Landing page", url="/", question="Summarize"),
        OrchestrationStep(description="Pricing", url="/pricing", question="What is the cost?"),
    ]

    result = orchestrator.run(default_plan)
    payload = {
        "steps": [asdict(step) for step in result.steps_executed],
        "browser_actions": [asdict(action) for action in result.browser_actions],
        "ai_transcripts": result.ai_transcripts,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    run_from_env()
