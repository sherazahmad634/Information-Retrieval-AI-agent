"""API-key authentication helpers."""

from __future__ import annotations

import secrets

from fastapi import Header

from app.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError


async def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """FastAPI dependency that enforces the X-API-Key header.

    If no API key is configured in settings, authentication is disabled
    (development convenience). In production, set ``API_KEY`` in the
    environment to require it.
    """
    settings: Settings = get_settings()
    expected = settings.api_key
    if not expected:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise UnauthorizedError("Invalid or missing API key.")
