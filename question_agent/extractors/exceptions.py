"""Shared exception hierarchy for all extractors."""


class ExtractionError(Exception):
    """Base exception for extraction failures."""

    def __init__(self, message: str, format: str | None = None):
        self.format = format
        super().__init__(message)
