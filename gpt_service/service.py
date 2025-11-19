"""REST/WebSocket service that exposes a local Hugging Face model."""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer, TextGenerationPipeline, pipeline

from .exceptions import TokenLimitError
from .tokenization import TokenBudget, simple_token_count

LOGGER = logging.getLogger(__name__)


class GenerationRequest(BaseModel):
    """Request body accepted by the REST endpoint."""

    prompt: str = Field(..., description="Prompt provided by the client.")
    max_new_tokens: int = Field(128, ge=1, le=2048)
    temperature: float = Field(0.7, ge=0.0, le=2.0)


class LocalModelService:
    """Thin wrapper around a Hugging Face text-generation pipeline."""

    def __init__(
        self,
        model_name: str = "distilgpt2",
        max_input_tokens: int = 2048,
        max_output_tokens: int = 512,
    ) -> None:
        self.model_name = model_name
        self.pipeline: TextGenerationPipeline = pipeline(
            "text-generation",
            model=AutoModelForCausalLM.from_pretrained(model_name),
            tokenizer=AutoTokenizer.from_pretrained(model_name),
        )
        self.budget = TokenBudget(max_input_tokens, max_output_tokens)

    def generate(self, *, prompt: str, max_new_tokens: int, temperature: float) -> dict[str, Any]:
        self.budget.validate_prompt(prompt)
        max_new_tokens = min(max_new_tokens, self.budget.max_output_tokens)
        LOGGER.debug("Generating with model %s", self.model_name)
        outputs = self.pipeline(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
        generated = outputs[0]["generated_text"]
        trimmed_completion = self.budget.clamp_output(generated)
        return {
            "prompt": prompt,
            "completion": trimmed_completion,
            "prompt_tokens": simple_token_count(prompt),
            "completion_tokens": simple_token_count(trimmed_completion),
        }

    async def stream_generate(self, *, prompt: str, max_new_tokens: int, temperature: float) -> AsyncIterator[str]:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                self.generate,
                prompt=prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
            ),
        )
        completion = result["completion"]
        chunk_size = max(1, len(completion) // 10)
        for start in range(0, len(completion), chunk_size):
            yield completion[start : start + chunk_size]


def build_app(service: LocalModelService | None = None) -> FastAPI:
    """Create a FastAPI application exposing REST and WebSocket interfaces."""

    service = service or LocalModelService()
    app = FastAPI(title="Local LLM Service", version="1.0.0")

    @app.post("/generate")
    async def generate_text(payload: GenerationRequest) -> JSONResponse:
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                partial(
                    service.generate,
                    prompt=payload.prompt,
                    max_new_tokens=payload.max_new_tokens,
                    temperature=payload.temperature,
                ),
            )
            return JSONResponse(
                {
                    **result,
                    "total_tokens": result["prompt_tokens"] + result["completion_tokens"],
                    "model": service.model_name,
                }
            )
        except TokenLimitError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_json()
                request = GenerationRequest(**data)
                try:
                    async for chunk in service.stream_generate(
                        prompt=request.prompt,
                        max_new_tokens=request.max_new_tokens,
                        temperature=request.temperature,
                    ):
                        await websocket.send_json({"chunk": chunk})
                    await websocket.send_json({"event": "end"})
                except TokenLimitError as exc:
                    await websocket.send_json({"error": str(exc)})
        except WebSocketDisconnect:
            LOGGER.info("WebSocket disconnected")

    return app


__all__ = ["LocalModelService", "build_app", "GenerationRequest"]
