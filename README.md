# GPT Service Helpers

This repository contains two complementary building blocks for working with
large language models (LLMs):

1. **`ExternalAPIClient`** – a hardened wrapper for calling a third-party
   completions endpoint with prompt/response validation, retry logic and
   structured logging.
2. **`LocalModelService`** – a FastAPI application that exposes a Hugging Face
   model through both REST and WebSocket interfaces while enforcing input and
   output token budgets.

Both components share a light-weight token counting helper so that requests are
clamped before they exceed the configured budgets.

## Project layout

```
.
├── gpt_service/
│   ├── api_wrapper.py      # External API integration
│   ├── exceptions.py       # Custom TokenLimitError
│   ├── service.py          # FastAPI service exposing a local model
│   └── tokenization.py     # Simple token counting helpers
├── run_service.py          # Convenience entrypoint for uvicorn
└── pyproject.toml
```

## External API usage

```python
from gpt_service import APIConfig, ExternalAPIClient

config = APIConfig(
    base_url="https://api.openai.com/v1/chat/completions",
    api_key="sk-...",
    model="gpt-4",
    max_input_tokens=4096,
    max_output_tokens=1024,
)

client = ExternalAPIClient(config)
response = client.generate("Explain how retry with exponential backoff works.")
print(response.completion)
```

The wrapper automatically:

- validates the prompt against your configured token budget
- retries transient HTTP failures with exponential backoff
- logs attempts and server responses via Python's standard `logging` module
- normalizes the response payload into a simple `APIResponse` dataclass

## Hosting your own model

The `LocalModelService` wraps a Hugging Face Transformers text-generation
pipeline and exposes two public interfaces:

- `POST /generate` accepts a JSON body containing the prompt, `max_new_tokens`
  and `temperature` and responds with the completion along with token counts.
- `GET /ws` exposes a WebSocket endpoint. Send the same payload as JSON and
  you'll receive incremental chunks followed by an `{ "event": "end" }` message.

### Running locally

Install the project (ideally inside a virtual environment):

```bash
pip install -e .
```

Then start the service:

```bash
python run_service.py
```

Environment variables let you control the hosted model and token budgets:

- `LLM_MODEL` (default `distilgpt2`)
- `LLM_MAX_INPUT_TOKENS` (default `2048`)
- `LLM_MAX_OUTPUT_TOKENS` (default `512`)

Once running, try a request:

```bash
curl -X POST http://localhost:8000/generate \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Write a haiku about FastAPI"}'
```

Or connect over WebSocket (example using `wscat`):

```bash
wscat -c ws://localhost:8000/ws
> {"prompt": "Summarize the benefits of token budgeting."}
< {"chunk": "Token budgets"}
< ...
< {"event": "end"}
```

## Respecting token limits

The shared `TokenBudget` utility provides deterministic token counting and
clamps responses to your declared limits. When either the input or output would
exceed the budget a `TokenLimitError` is raised (or serialized as a `400`
response from the FastAPI layer), making the behaviour explicit to API
consumers.
