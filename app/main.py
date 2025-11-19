"""FastAPI application exposing Playwright-powered browser automation endpoints."""
from __future__ import annotations

import base64
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from .session_manager import SessionManager

app = FastAPI(title="Playwright Session Gateway")
session_manager = SessionManager(max_sessions=5, session_ttl=900)


class CreateSessionRequest(BaseModel):
    browser: Literal["chromium", "firefox", "webkit"] = Field(
        default="chromium", description="Browser engine to launch"
    )
    headless: bool = Field(default=True, description="Launch browser in headless mode")


class CreateSessionResponse(BaseModel):
    session_id: str


class NavigateRequest(BaseModel):
    url: HttpUrl
    wait_until: Literal["load", "domcontentloaded", "networkidle"] = "load"


class SelectorRequest(BaseModel):
    selector: str
    timeout_ms: Optional[int] = Field(default=10000, description="Selector wait timeout in milliseconds")


class TextResponse(BaseModel):
    text: Optional[str]


class TextAllRequest(BaseModel):
    selector: str
    timeout_ms: Optional[int] = 10000
    all_matches: bool = False


class ScreenshotRequest(BaseModel):
    selector: Optional[str] = None
    full_page: bool = True
    omit_background: bool = True


class ScreenshotResponse(BaseModel):
    screenshot: str


@app.on_event("startup")
async def _startup() -> None:
    await session_manager.start()


@app.on_event("shutdown")
async def _shutdown() -> None:
    await session_manager.stop()


@app.post("/sessions", response_model=CreateSessionResponse)
async def create_session(payload: CreateSessionRequest) -> CreateSessionResponse:
    try:
        session_id = await session_manager.create_session(
            browser_name=payload.browser, headless=payload.headless
        )
        return CreateSessionResponse(session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/sessions")
async def list_sessions() -> dict:
    return await session_manager.summary()


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    await session_manager.close_session(session_id)
    return {"status": "closed"}


@app.post("/sessions/{session_id}/navigate")
async def navigate(session_id: str, payload: NavigateRequest) -> dict:
    page = await _page_for(session_id)
    try:
        await page.goto(payload.url, wait_until=payload.wait_until)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "navigated", "url": payload.url}


@app.post("/sessions/{session_id}/click")
async def click(session_id: str, payload: SelectorRequest) -> dict:
    page = await _page_for(session_id)
    try:
        timeout = payload.timeout_ms or 10000
        await page.click(payload.selector, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "clicked", "selector": payload.selector}


@app.post("/sessions/{session_id}/text", response_model=TextResponse)
async def extract_text(session_id: str, payload: TextAllRequest) -> TextResponse:
    page = await _page_for(session_id)
    try:
        if payload.all_matches:
            timeout = payload.timeout_ms or 10000
            await page.wait_for_selector(payload.selector, timeout=timeout)
            handles = await page.query_selector_all(payload.selector)
            texts = [await handle.inner_text() for handle in handles]
            text = "\n".join(texts)
        else:
            timeout = payload.timeout_ms or 10000
            handle = await page.wait_for_selector(payload.selector, timeout=timeout)
            text = await handle.inner_text() if handle else None
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return TextResponse(text=text)


@app.post("/sessions/{session_id}/screenshot", response_model=ScreenshotResponse)
async def screenshot(session_id: str, payload: ScreenshotRequest) -> ScreenshotResponse:
    page = await _page_for(session_id)
    try:
        if payload.selector:
            element = await page.wait_for_selector(payload.selector)
            binary = await element.screenshot(omit_background=payload.omit_background)
        else:
            binary = await page.screenshot(full_page=payload.full_page, omit_background=payload.omit_background)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    encoded = base64.b64encode(binary).decode("utf-8")
    return ScreenshotResponse(screenshot=encoded)


async def _page_for(session_id: str):
    try:
        return await session_manager.get_page(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
