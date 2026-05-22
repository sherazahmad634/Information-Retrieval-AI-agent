"""Document ingestion / update tool — lets the agent extend its own corpus."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.services.tools.base import Tool, ToolError, ToolResult

if TYPE_CHECKING:
    from app.services.ingestion import IngestionService


class DocumentIngestTool(Tool):
    """Add a new document (raw text) to the user's indexed corpus."""

    name = "document_ingest"
    description = (
        "Ingest raw text content as a new document in the corpus so future searches can "
        "retrieve it. Use this when the user asks to remember, save, note, or learn a "
        "piece of information. Also use it to capture findings from web search that the "
        "user wants to keep. Returns the new document's ID."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short human-readable title for the document.",
            },
            "content": {
                "type": "string",
                "description": "Full text content to ingest. May be long.",
            },
            "source": {
                "type": "string",
                "description": "Origin label, e.g. 'user-note', 'web:example.com'.",
            },
        },
        "required": ["title", "content"],
        "additionalProperties": False,
    }

    def __init__(self, ingestion: "IngestionService") -> None:
        self._ingestion = ingestion

    async def run(self, **kwargs: Any) -> ToolResult:
        title = kwargs.get("title")
        content = kwargs.get("content")
        source = kwargs.get("source") or "agent-ingest"
        if not isinstance(title, str) or not title.strip():
            raise ToolError("`title` is required.")
        if not isinstance(content, str) or not content.strip():
            raise ToolError("`content` is required.")

        doc = await self._ingestion.ingest_text(
            title=title.strip(),
            text=content,
            source=source,
            content_type="text/plain",
        )
        return ToolResult(
            content=(
                f"Ingested document '{doc.title}' (id={doc.id}) with {doc.chunk_count} chunks "
                f"({doc.char_count} characters). It is now searchable."
            ),
            data={
                "document_id": doc.id,
                "title": doc.title,
                "chunks_created": doc.chunk_count,
                "char_count": doc.char_count,
            },
        )
