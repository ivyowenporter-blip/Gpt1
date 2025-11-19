# Gpt1 Automation Harness

This repository provides a lightweight harness that mimics the interaction
between browser automation, AI prompt orchestration, and a deterministic loop
that glues the two together. It is intentionally framework-free so you can plug
in your own browser runners or LLM clients.

## Project layout

```
src/gpt1/        # Browser, AI, and orchestration building blocks
src/gpt1/cli.py  # Entry point that wires everything together for demos
tests/           # Pytest-based automated tests
```

## Getting started

1. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the automated tests**
   ```bash
   pytest
   ```

3. **Execute the demo orchestrator**
   ```bash
   python -m gpt1.cli
   ```

## Environment variables

| Name | Default | Description |
| --- | --- | --- |
| `BROWSER_BASE_URL` | `https://example.com` | Base URL that the browser session uses when resolving relative paths. |
| `AI_MODEL_NAME` | `mock-gpt` | Model identifier injected into prompts for traceability. |
| `ORCHESTRATOR_MAX_STEPS` | `5` | Safety valve that caps the orchestration loop. |

## Docker

Build a portable container image that ships the CLI and tests.

```bash
docker build -t gpt1:latest .
```

Run the demo orchestration loop with custom environment variables:

```bash
docker run --rm -e BROWSER_BASE_URL=https://docs.example.com gpt1:latest
```

## Continuous integration

GitHub Actions is configured (see `.github/workflows/tests.yml`) to install
Python dependencies, run the full Pytest suite, and surface failures in pull
requests.

## Security recommendations

* Secrets scrubbing: `PromptTemplateAIAgent` masks obvious secrets using a
  regex-based scrubber before building prompts. Extend `SENSITIVE_PATTERNS` to
  cover organization-specific tokens.
* Principle of least privilege: configure `BROWSER_BASE_URL` to point at mock or
  staging systems when experimenting with automated browser actions.
* Deterministic mocks: The default LLM client and browser fetcher keep execution
  deterministic so telemetry logs remain predictable and safe to share.

## Deployment checklist

1. Run the automated tests locally (`pytest`).
2. Build and scan the Docker image.
3. Configure GitHub repository secrets for any real LLM credentials before
   swapping in production clients.
4. Wire the CLI entry point into your scheduler or workflow engine of choice.
