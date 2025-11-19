from gpt1.ai import PromptTemplateAIAgent
from gpt1.browser import BrowserSession
from gpt1.orchestration import OrchestrationStep, TaskOrchestrator


def test_orchestrator_runs_plan_and_respects_step_limit():
    fetches = {}

    def fake_fetcher(url: str) -> str:
        fetches[url] = f"Content for {url}"
        return fetches[url]

    browser = BrowserSession(base_url="https://example.com", fetcher=fake_fetcher)
    agent = PromptTemplateAIAgent(model_name="orchestrator-test", llm_client=lambda prompt: prompt.upper())
    orchestrator = TaskOrchestrator(browser=browser, agent=agent, max_steps=1)

    plan = [
        OrchestrationStep(description="One", url="/one", question="Q1"),
        OrchestrationStep(description="Two", url="/two", question="Q2"),
    ]

    result = orchestrator.run(plan)

    assert len(result.steps_executed) == 1
    assert result.steps_executed[0].description == "One"
    assert len(result.browser_actions) == 1
    assert result.ai_transcripts[0].startswith("MODEL=ORCHESTRATOR-TEST")
    assert "https://example.com/one" in fetches
