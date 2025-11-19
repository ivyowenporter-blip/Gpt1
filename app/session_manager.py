"""Browser session management utilities built around Playwright."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Optional
from uuid import uuid4

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright


@dataclass
class _SessionState:
    browser: Browser
    context: BrowserContext
    page: Page
    created_at: float
    last_used: float

    def touch(self) -> None:
        now = time.time()
        self.last_used = now


class SessionManager:
    """Creates, tracks, and cleans up Playwright browser sessions."""

    def __init__(self, *, max_sessions: int = 10, session_ttl: int = 600) -> None:
        self._max_sessions = max_sessions
        self._session_ttl = session_ttl
        self._sessions: Dict[str, _SessionState] = {}
        self._playwright: Optional[Playwright] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._playwright is None:
            self._playwright = await async_playwright().start()

    async def stop(self) -> None:
        async with self._lock:
            for session_id in list(self._sessions.keys()):
                await self._close_session(session_id)
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None

    async def create_session(self, *, browser_name: str = "chromium", headless: bool = True) -> str:
        if self._playwright is None:
            raise RuntimeError("SessionManager has not been started")

        async with self._lock:
            await self._expire_old_sessions()
            if len(self._sessions) >= self._max_sessions:
                raise RuntimeError("Maximum number of browser sessions reached")

            browser_factory = getattr(self._playwright, browser_name, None)
            if browser_factory is None:
                raise ValueError(f"Unsupported browser '{browser_name}'")

            browser = await browser_factory.launch(headless=headless)
            context = await browser.new_context()
            page = await context.new_page()

            session_id = uuid4().hex
            now = time.time()
            self._sessions[session_id] = _SessionState(
                browser=browser,
                context=context,
                page=page,
                created_at=now,
                last_used=now,
            )
            return session_id

    async def get_page(self, session_id: str) -> Page:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Session '{session_id}' was not found")
        session.touch()
        return session.page

    async def close_session(self, session_id: str) -> None:
        async with self._lock:
            await self._close_session(session_id)

    async def _close_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return
        await session.context.close()
        await session.browser.close()

    async def _expire_old_sessions(self) -> None:
        now = time.time()
        expired = [sid for sid, session in self._sessions.items() if now - session.last_used > self._session_ttl]
        for session_id in expired:
            await self._close_session(session_id)

    async def summary(self) -> Dict[str, Dict[str, float]]:
        return {
            session_id: {
                "created_at": session.created_at,
                "last_used": session.last_used,
            }
            for session_id, session in self._sessions.items()
        }
