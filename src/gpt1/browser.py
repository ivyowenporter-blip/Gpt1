"""Simple browser simulation utilities for deterministic tests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional
from urllib.parse import urljoin


@dataclass
class BrowserAction:
    """Represents a browser interaction for later assertions."""

    action: str
    target: str
    value: Optional[str] = None


class BrowserSession:
    """Minimal browser session abstraction.

    The session records every action so automated tests can assert the exact
    behavior without relying on a real browser or WebDriver binary.
    """

    def __init__(self, base_url: str, fetcher: Optional[Callable[[str], str]] = None):
        self.base_url = base_url
        self._fetcher = fetcher or (lambda url: f"<html>Placeholder content for {url}</html>")
        self.actions: List[BrowserAction] = []

    def _record(self, action: str, target: str, value: Optional[str] = None) -> BrowserAction:
        entry = BrowserAction(action=action, target=target, value=value)
        self.actions.append(entry)
        return entry

    def open_page(self, path: str) -> str:
        url = urljoin(self.base_url, path)
        content = self._fetcher(url)
        self._record("open", url, value=content)
        return content

    def click(self, selector: str) -> None:
        self._record("click", selector)

    def type_text(self, selector: str, value: str) -> None:
        self._record("type", selector, value=value)

    def snapshot(self) -> List[BrowserAction]:
        """Return a shallow copy of recorded actions for assertions."""

        return list(self.actions)
