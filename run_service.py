"""Entrypoint for hosting the local language model service via uvicorn."""

from __future__ import annotations

import logging
import os

import uvicorn

from gpt_service.service import LocalModelService, build_app

logging.basicConfig(level=logging.INFO)


def main() -> None:
    model_name = os.getenv("LLM_MODEL", "distilgpt2")
    max_input = int(os.getenv("LLM_MAX_INPUT_TOKENS", "2048"))
    max_output = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "512"))

    service = LocalModelService(
        model_name=model_name,
        max_input_tokens=max_input,
        max_output_tokens=max_output,
    )
    app = build_app(service)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
