from gpt1.ai import PromptTemplateAIAgent, scrub_sensitive_data


def test_scrubber_masks_sensitive_tokens():
    text = "API_KEY=secret-token"
    sanitized = scrub_sensitive_data(text)
    assert "API_KEY"[0] in sanitized
    assert "*" in sanitized


def test_agent_builds_safe_prompt_and_uses_client():
    captured = {}

    def fake_client(prompt: str) -> str:
        captured["prompt"] = prompt
        return "ok"

    agent = PromptTemplateAIAgent(model_name="x", llm_client=fake_client)
    result = agent.generate("my secret", "api_key please")

    assert result["response"] == "ok"
    assert "secret" not in captured["prompt"].lower()
    assert "api_key" not in captured["prompt"].lower()
