"""Custom exceptions used throughout the GPT service helpers."""


class TokenLimitError(ValueError):
    """Raised when an input or output would exceed the configured token limit."""

    def __init__(self, message: str, *, tokens: int | None = None, limit: int | None = None) -> None:
        super().__init__(message)
        self.tokens = tokens
        self.limit = limit

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"TokenLimitError(message={self.args[0]!r}, tokens={self.tokens}, limit={self.limit})"
