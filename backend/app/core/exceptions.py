"""Application-level exceptions.

Exceptions are kept in a small hierarchy rooted at ``IRAgentError`` so that
the API layer can map them to HTTP responses in one place.
"""

from __future__ import annotations


class IRAgentError(Exception):
    """Base class for all application errors."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(IRAgentError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    code = "not_found"


class ValidationError(IRAgentError):
    """Raised when user input fails domain validation."""

    status_code = 422
    code = "validation_error"


class UnauthorizedError(IRAgentError):
    """Raised when a request lacks valid credentials."""

    status_code = 401
    code = "unauthorized"


class IngestionError(IRAgentError):
    """Raised when document parsing or ingestion fails."""

    status_code = 400
    code = "ingestion_error"


class RetrievalError(IRAgentError):
    """Raised by the retrieval pipeline on unrecoverable failure."""

    status_code = 503
    code = "retrieval_error"


class LLMError(IRAgentError):
    """Raised when the LLM provider fails or returns an invalid response."""

    status_code = 502
    code = "llm_error"
