"""FastAPI application entrypoint.

Composes the dependency container, registers middleware, mounts the routers,
and installs uniform exception handlers.

Run locally:

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.deps import AppContainer
from app.api.middleware import RequestContextMiddleware
from app.api.routes import chat, documents, health, search, tools
from app.config import Settings, get_settings
from app.core.exceptions import IRAgentError
from app.core.logging import configure_logging, get_logger, get_request_id
from app.core.security import verify_api_key
from app.models.schemas import ErrorResponse

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise heavy services on startup and tear them down on shutdown."""
    settings: Settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.is_production)
    logger.info("starting_app", env=settings.app_env, version=settings.app_version)

    container = AppContainer(settings)
    await container.startup()
    app.state.container = container
    app.state.settings = settings

    logger.info(
        "ready",
        tools=container.tools.names(),
        embedding_dim=container.embedder.dimension,
        documents=await container.document_store.count(),
        chunks=await container.vector_store.count(),
    )
    try:
        yield
    finally:
        logger.info("shutting_down")


def create_app() -> FastAPI:
    """Application factory — used by uvicorn and the test suite."""
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.is_production)

    app = FastAPI(
        title="IR-Agent API",
        description=(
            "Information Retrieval AI Agent — hybrid retrieval, function-calling "
            "tool use, working memory, and grounded answers with citations."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ---- Middleware --------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)

    # ---- Rate limiting -----------------------------------------------------
    limiter = Limiter(
        key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"]
    )
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(_: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=ErrorResponse(
                code="rate_limited",
                message=str(exc.detail),
                request_id=get_request_id(),
            ).model_dump(),
        )

    # ---- Domain exception handler -----------------------------------------
    @app.exception_handler(IRAgentError)
    async def _domain_error(_: Request, exc: IRAgentError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                details=exc.details or None,
                request_id=get_request_id(),
            ).model_dump(),
        )

    # ---- Routers -----------------------------------------------------------
    from fastapi import Depends

    secured = [Depends(verify_api_key)] if settings.api_key else []
    prefix = settings.api_prefix

    app.include_router(health.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix, dependencies=secured)
    app.include_router(search.router, prefix=prefix, dependencies=secured)
    app.include_router(chat.router, prefix=prefix, dependencies=secured)
    app.include_router(tools.router, prefix=prefix, dependencies=secured)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "api": prefix,
        }

    return app


app = create_app()
