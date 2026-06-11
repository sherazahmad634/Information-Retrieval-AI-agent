"""FastAPI dependency-injection wiring.

A single :class:`AppContainer` is constructed once at startup and stored on
``app.state``. The dependency callables below pull individual collaborators
out of the container so route handlers can declare just what they need.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.repositories.document_store import DocumentStore
from app.repositories.vector_store import (
    ChromaVectorStore,
    InMemoryVectorStore,
    VectorStore,
)
from app.services.agent import ToolUsingAgent
from app.services.embedder import (
    Embedder,
    MockEmbedder,
    SentenceTransformersEmbedder,
)
from app.services.ingestion import IngestionService
from app.services.memory import MemoryService, WorkingMemory
from app.services.openai_client import build_openai_client
from app.services.parsers import ParserRegistry
from app.services.reranker import (
    CrossEncoderReranker,
    NoOpReranker,
    Reranker,
)
from app.services.retriever import HybridRetriever
from app.services.tools.calculator import CalculatorTool
from app.services.tools.document_ingest import DocumentIngestTool
from app.services.tools.document_search import DocumentSearchTool
from app.services.tools.memory_tool import RecallTool, RememberTool
from app.services.tools.registry import ToolRegistry
from app.services.tools.web_search import TavilyWebSearchTool, WebSearchTool
from app.utils.chunker import ChunkerConfig, TextChunker


class AppContainer:
    """Holds long-lived service instances for the lifetime of the app."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embedder: Embedder = self._build_embedder(settings)
        self.reranker: Reranker = self._build_reranker(settings)
        self.vector_store: VectorStore = self._build_vector_store(settings)
        self.document_store = DocumentStore(settings.document_store_path)
        self.long_term_memory = MemoryService(
            path=str(settings.document_store_path).replace(".db", "_memory.db")
        )
        self.working_memory = WorkingMemory(max_turns=20)
        self.parsers = ParserRegistry()
        self.chunker = TextChunker(
            ChunkerConfig(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
        )
        self.retriever = HybridRetriever(
            vector_store=self.vector_store,
            embedder=self.embedder,
            reranker=self.reranker,
            top_k_retrieval=settings.top_k_retrieval,
            top_k_rerank=settings.top_k_rerank,
            rrf_k=settings.rrf_k,
        )
        self.ingestion = IngestionService(
            parsers=self.parsers,
            chunker=self.chunker,
            embedder=self.embedder,
            vector_store=self.vector_store,
            document_store=self.document_store,
            retriever=self.retriever,
        )
        self.tools = self._build_tools()
        self.openai_client = build_openai_client(settings)
        self.agent = ToolUsingAgent(
            openai_client=self.openai_client,
            model=settings.llm_model,
            tools=self.tools,
            document_store=self.document_store,
            working_memory=self.working_memory,
            long_term_memory=self.long_term_memory,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            use_mock=settings.use_mock_llm,
        )

    async def startup(self) -> None:
        """Run async initialisation that can't happen in __init__."""
        await self.document_store.init()
        await self.long_term_memory.init()

    # -------------------------------------------------------------- factories

    @staticmethod
    def _build_embedder(settings: Settings) -> Embedder:
        if settings.embedding_provider == "mock" or settings.use_mock_llm:
            return MockEmbedder(dimension=settings.embedding_dimension)
        return SentenceTransformersEmbedder(model_name=settings.embedding_model)

    @staticmethod
    def _build_reranker(settings: Settings) -> Reranker:
        if not settings.reranker_enabled or settings.use_mock_llm:
            return NoOpReranker()
        return CrossEncoderReranker(model_name=settings.reranker_model)

    @staticmethod
    def _build_vector_store(settings: Settings) -> VectorStore:
        if settings.vector_store_provider == "memory":
            return InMemoryVectorStore()
        return ChromaVectorStore(
            path=settings.vector_store_path,
            collection_name=settings.vector_store_collection,
        )

    def _build_tools(self) -> ToolRegistry:
        if (
            self.settings.web_search_provider == "tavily"
            and self.settings.tavily_api_key
        ):
            web_search_tool = TavilyWebSearchTool(api_key=self.settings.tavily_api_key)
        else:
            web_search_tool = WebSearchTool()

        return ToolRegistry(
            tools=[
                DocumentSearchTool(self.retriever),
                DocumentIngestTool(self.ingestion),
                web_search_tool,
                CalculatorTool(),
                RememberTool(self.long_term_memory),
                RecallTool(self.long_term_memory),
            ]
        )


# ---------------------------------------------------------------------------
# FastAPI dependency callables
# ---------------------------------------------------------------------------


def get_container(request: Request) -> AppContainer:
    """Return the shared :class:`AppContainer` from ``app.state``."""
    container: AppContainer = request.app.state.container
    return container


SettingsDep = Annotated[Settings, Depends(get_settings)]
ContainerDep = Annotated[AppContainer, Depends(get_container)]


def get_agent(container: ContainerDep) -> ToolUsingAgent:
    return container.agent


def get_retriever(container: ContainerDep) -> HybridRetriever:
    return container.retriever


def get_ingestion(container: ContainerDep) -> IngestionService:
    return container.ingestion


def get_document_store(container: ContainerDep) -> DocumentStore:
    return container.document_store


def get_vector_store(container: ContainerDep) -> VectorStore:
    return container.vector_store


def get_tools(container: ContainerDep) -> ToolRegistry:
    return container.tools


AgentDep = Annotated[ToolUsingAgent, Depends(get_agent)]
RetrieverDep = Annotated[HybridRetriever, Depends(get_retriever)]
IngestionDep = Annotated[IngestionService, Depends(get_ingestion)]
DocumentStoreDep = Annotated[DocumentStore, Depends(get_document_store)]
VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
ToolsDep = Annotated[ToolRegistry, Depends(get_tools)]
