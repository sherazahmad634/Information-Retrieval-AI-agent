"""Document search tool — the agent's primary IR skill."""

from __future__ import annotations

from typing import Any

from app.services.retriever import HybridRetriever
from app.services.tools.base import Tool, ToolError, ToolResult


class DocumentSearchTool(Tool):
    """Hybrid (BM25 + dense + rerank) search over the indexed corpus."""

    name = "document_search"
    description = (
        "Search the user's private indexed document corpus and return the most relevant "
        "passages. Always call this tool first when the question is likely about the "
        "user's own knowledge base, internal documents, or any topic that may already be "
        "indexed. Returns ranked passages with citation IDs."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language search query. Use the user's words.",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of passages to return (1-10). Defaults to 5.",
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(self, retriever: HybridRetriever) -> None:
        self._retriever = retriever

    async def run(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query")
        top_k = int(kwargs.get("top_k") or 5)
        if not isinstance(query, str) or not query.strip():
            raise ToolError("`query` is required and must be a non-empty string.")

        scored = await self._retriever.retrieve(query, top_k=top_k)
        if not scored:
            return ToolResult(
                content="No relevant passages were found in the indexed corpus.",
                data={"results": []},
            )

        lines = [f"Found {len(scored)} relevant passages:"]
        results: list[dict[str, Any]] = []
        for idx, sc in enumerate(scored, start=1):
            lines.append(
                f"[{idx}] (score={sc.score:.3f}, source={sc.source}) "
                f"doc={sc.chunk.document_id} chunk={sc.chunk.position}\n"
                f"{sc.chunk.text[:600]}"
            )
            results.append(
                {
                    "rank": idx,
                    "chunk_id": sc.chunk.id,
                    "document_id": sc.chunk.document_id,
                    "position": sc.chunk.position,
                    "score": round(sc.score, 4),
                    "source": sc.source,
                    "text": sc.chunk.text,
                }
            )
        return ToolResult(content="\n\n".join(lines), data={"results": results})
